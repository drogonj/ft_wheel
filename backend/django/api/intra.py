import os, time, asyncio, httpx, logging, queue
from asgiref.sync import async_to_sync
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler

from custom_auth.views import oauth_secrets

# ---------------------
# non-blocking logging setup
# ---------------------
LOG_DIR = "/var/log/ft_wheel"
os.makedirs(LOG_DIR, exist_ok=True)

log_queue = queue.Queue(-1)  # file-backed queue handled by QueueListener thread

file_info_path = os.path.join(LOG_DIR, "intra_info.log")
file_error_path = os.path.join(LOG_DIR, "intra_error.log")

file_handler_info = RotatingFileHandler(file_info_path, maxBytes=10 * 1024 * 1024, backupCount=3)
file_handler_info.setLevel(logging.INFO)
file_handler_info.addFilter(lambda record: record.levelno <= logging.INFO)
file_handler_error = RotatingFileHandler(file_error_path, maxBytes=10 * 1024 * 1024, backupCount=3)
file_handler_error.setLevel(logging.ERROR)
file_handler_error.addFilter(lambda record: record.levelno >= logging.ERROR)


formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler_info.setFormatter(formatter)
file_handler_error.setFormatter(formatter)

# QueueListener will consume log_queue and write to handlers on a background thread.
_queue_listener = QueueListener(log_queue, file_handler_info, file_handler_error)
_queue_listener.start()

logger = logging.getLogger("intra")
logger.setLevel(logging.INFO)
logger.addHandler(QueueHandler(log_queue))


# ---------------------
# Async Intra API class
# Use IntraAPI instead for sync contexts
# ---------------------
class AsyncIntraAPI:
    """
    Async client for the 42 intra API.
    Designed to be used with asyncio (await) or with asgiref.sync.async_to_sync
    from sync contexts.
    """

    TOKEN_URL = "https://api.intra.42.fr/oauth/token"

    def __init__(self, client_id: str = None, client_secret: str = None, api_url: str = "https://api.intra.42.fr/v2"):
        # If not provided, fallback to oauth_secrets imported from custom_auth.views
        self.client_id = client_id if client_id is not None else oauth_secrets.get("oauth_uid")
        self.client_secret = client_secret if client_secret is not None else oauth_secrets.get("oauth_secret")
        self.api_url = api_url

        # token state (kept in-memory)
        self._token = None
        self._token_created_at = 0
        self._token_expires_in = 0

        # async lock to protect token refresh inside the same event loop / process
        # we create lazily to avoid loop-binding corner cases
        self._token_lock = None  # will be set to asyncio.Lock() when first needed

        # reuse AsyncClient to benefit from connection pooling
        self._client = httpx.AsyncClient(timeout=30.0)

    def _token_valid(self) -> bool:
        if not self._token:
            return False
        now = int(time.time())
        # small safety margin (10 seconds) to avoid using just-expired token
        return now < (self._token_created_at + self._token_expires_in - 10)

    async def get_token(self):
        """
        Return a valid token, fetching a new one if needed.
        Uses double-checked locking with an asyncio.Lock to ensure a single fetch.
        """
        if self._token_valid():
            logger.debug("Using existing token")
            return self._token

        # lazy-create the lock so it's created in a running-loop context
        if self._token_lock is None:
            # safe to create a Lock here; it will be awaited in an async context
            self._token_lock = asyncio.Lock()

        async with self._token_lock:
            # double-check inside lock
            if self._token_valid():
                logger.debug("Token became valid while waiting for lock")
                return self._token

            # fetch new token using client_credentials grant
            try:
                logger.info("Fetching new OAuth2 token from 42 API")
                resp = await self._client.post(
                    self.TOKEN_URL,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    },
                    timeout=10.0
                )
                resp.raise_for_status()
                token = resp.json()
                # token may include 'created_at' (epoch) and 'expires_in'
                self._token = token
                self._token_created_at = token.get("created_at", int(time.time()))
                self._token_expires_in = token.get("expires_in", 3600)
                logger.info("Fetched new token successfully")
                return self._token
            except Exception as e:
                # log and re-raise: caller can handle retry logic
                logger.exception(f"Error fetching token: {e}")
                raise

    async def request(self, method: str, url: str, headers: dict = None, **kwargs):
        """
        Make an authenticated HTTP request to the Intra API.

        Keeps the original semantics:
        - retry up to 3 attempts
        - respects Retry-After on 429
        - distinguishes client (4xx) and server (>=500) errors
        - logs responses
        """
        if not url.startswith("http"):
            full_url = self.api_url + url
        else:
            full_url = url

        attempts = 0

        while attempts < 3:
            attempts += 1

            # ensure we have a token (this may raise if token fetch fails)
            try:
                token = await self.get_token()
            except Exception as e:
                # if we fail to obtain token, no point retrying this loop (or we could)
                logger.error(f"Failed to obtain token before request to {full_url}: {e}")
                raise

            # prepare headers
            req_headers = dict(headers) if headers else {}
            req_headers["Authorization"] = f"Bearer {token['access_token']}"

            try:
                resp = await self._client.request(method, full_url, headers=req_headers, **kwargs)
                rc = resp.status_code

                # Rate limit -> respect Retry-After and retry
                if rc == 429:
                    retry_after = resp.headers.get("Retry-After")
                    try:
                        sleep_seconds = float(retry_after) if retry_after is not None else 1.0
                    except Exception:
                        sleep_seconds = 1.0
                    logger.warning(f"Rate limited on {full_url}. Retry-After: {sleep_seconds}s")
                    await asyncio.sleep(sleep_seconds)
                    continue

                # Authorization problem -> invalidate token and retry once
                if rc == 401:
                    logger.warning("Received 401 Unauthorized; invalidating token and retrying")
                    self._token = None
                    self._token_created_at = 0
                    self._token_expires_in = 0
                    # small backoff then retry
                    await asyncio.sleep(0.5)
                    continue

                if rc >= 400:
                    content = resp.text
                    if rc < 500:
                        # client error: don't retry further (mirrors original behavior)
                        logger.error(f"Client error {rc} on {method} {full_url}: {content}")
                        raise ValueError(f"\n{dict(resp.headers)}\n\nClientError. Error {rc}\n{content}\n")
                    else:
                        # server error: allow retry according to attempts loop
                        logger.error(f"Server error {rc} on {method} {full_url}: {content}")
                        raise ValueError(f"\n{dict(resp.headers)}\n\nServerError. Error {rc}\n{content}\n")

                # Success path: log and return JSON
                try:
                    body = resp.json()
                except Exception:
                    # in case response is not JSON, fall back to text
                    body = resp.text
                logger.info(f"Success {method} {full_url}: {body}")
                return body

            except ValueError:
                # these are re-raised client/server errors
                # if attempts exhausted, raise; otherwise, if server error, we will end up retrying
                if attempts >= 3:
                    logger.error(f"Failed {method} {full_url} after {attempts} attempts (status error)")
                    raise
                # backoff
                await asyncio.sleep(1)
                continue

            except Exception as e:
                # network errors, timeouts, unexpected exceptions
                logger.exception(f"Request error on attempt {attempts} for {method} {full_url}: {e}")
                if attempts >= 3:
                    logger.error(f"Failed to make {method} request to {full_url} after {attempts} attempts. Error: {e}")
                    raise
                await asyncio.sleep(1)
                continue

        # if we exit the loop without returning we consider it a failure
        raise RuntimeError(f"Failed {method} {full_url} after {attempts} attempts")

    def intra_logger(self, kind: str, message: str):
        """
        Backwards-compatible logger method (keeps same API as before).
        Writes to the queue logger (non-blocking).
        """
        kind_upper = (kind or "INFO").upper()
        if kind_upper == "ERROR":
            logger.error(message)
        else:
            logger.info(message)

    async def close(self):
        """Close underlying HTTP client. Call on shutdown if desired."""
        try:
            await self._client.aclose()
        except Exception:
            logger.exception("Error when closing AsyncIntraAPI client")


# ---------------------
# Sync wrapper for AsyncIntraAPI
# ---------------------
class IntraAPI():
    """
    Synchronous wrapper around AsyncIntraAPI for use in sync contexts.
    Uses asgiref.sync.async_to_sync to call async methods.
    """
    def __init__(self, client_id: str = None, client_secret: str = None, api_url: str = "https://api.intra.42.fr/v2"):
        self._async_api = AsyncIntraAPI(client_id, client_secret, api_url)

    def request(self, method: str, url: str, headers: dict = None, **kwargs):
        """
        Placeholder for async_to_sync wrapped method.
        This will be replaced in __init__.
        """
        try:
            return async_to_sync(self._async_api.request)(method, url, headers, **kwargs)
        except Exception as e:
            raise e


# ---------------------
# Export single instance
# ---------------------
intra_api = IntraAPI(
    client_id=oauth_secrets.get("oauth_uid"),
    client_secret=oauth_secrets.get("oauth_secret"),
    api_url="https://api.intra.42.fr/v2"
)






    # def get_user_coa(self, login, fields=None):
    #     """
    #     Fetches the coalitions data for a user from the 42 API by login.
    #     Args:
    #         login (str): The login of the user.
    #         fields (list, optional): List of fields to return from the coalition data.
    #                                  If None, returns all fields.
    #     """
    #     url = f'https://api.intra.42.fr/v2/users/{login}/coalitions'
    #     response = self.get(url)

    #     if response and len(response) > 0:
    #         if fields:
    #             return [{field: coalition.get(field) for field in fields if field in coalition} for coalition in response]
    #         return response
    #     else:
    #         print(f"Coalition data for user with login '{login}' not found.")
    #         return None 