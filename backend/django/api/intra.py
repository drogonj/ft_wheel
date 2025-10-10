import time, asyncio, httpx
from asgiref.sync import async_to_sync

from ft_wheel.utils import docker_secret

oauth_secrets = {
    'oauth_uid': docker_secret("oauth_uid"),
    'oauth_secret': docker_secret("oauth_secret"),
}
    

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

    def __init__(self, client_id: str = None, client_secret: str = None, api_url: str = "https://api.intra.42.fr"):
        # If not provided, fallback to oauth_secrets imported from users.views
        self.client_id = client_id if client_id is not None else oauth_secrets.get("oauth_uid")
        self.client_secret = client_secret if client_secret is not None else oauth_secrets.get("oauth_secret")
        self.api_url = api_url

        # token state (kept in-memory)
        self._token = None
        self._token_expiry_ts = 0.0 # timestamp when token expires
        # async lock(s): handle errors with multiple event loops
        self._locks_by_loop: dict[asyncio.AbstractEventLoop, asyncio.Lock] = {}

        # reuse AsyncClient to benefit from connection pooling
        self._client = httpx.AsyncClient(timeout=30.0)

    def _token_valid(self) -> bool:
        if not self._token:
            return False
        return time.time() < (self._token_expiry_ts)

    async def _get_token(self):
        """
        Return a valid token, fetching a new one if needed.
        Lock par event loop pour éviter les cross-loop issues.
        """
        if self._token_valid():
            return self._token

        loop = asyncio.get_running_loop()
        lock = self._locks_by_loop.get(loop)
        if lock is None:
            lock = asyncio.Lock()
            self._locks_by_loop[loop] = lock

        async with lock:
            if self._token_valid():
                return self._token

            # fetch new token
            resp = await self._client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "public profile tig"
                },
                timeout=10.0
            )
            resp.raise_for_status()
            token = resp.json()

            now = time.time()
            expires_in = token.get("expires_in", 3600)
            # fallback if the value is missing/incorrect
            if not isinstance(expires_in, (int, float)) or expires_in <= 0:
                expires_in = 3600
            # small safety margin
            self._token_expiry_ts = now + expires_in - 10

            self._token = token
            return self._token


    async def request(self, method: str, url: str, headers: dict = None, **kwargs) -> tuple[bool, str, dict]:
        """
        Make an authenticated HTTP request to the Intra API.

        Returns:
            tuple[bool, str, dict]: (success, message, data)
            - success: True if request succeeded (2xx), False otherwise
            - message: Status message or error description
            - data: Response body as dict (empty dict {} if error or non-JSON)
        """
        if not url.startswith("http"):
            full_url = self.api_url + url
        else:
            full_url = url

        attempts = 0
        while attempts < 3:
            attempts += 1

            # ensure we have a token
            try:
                token = await self._get_token()
            except Exception as e:
                return False, f"Token fetch failed: {str(e)}", {}

            # prepare headers
            req_headers = dict(headers) if headers else {}
            req_headers["Authorization"] = f"Bearer {token['access_token']}"

            try:
                # Do the request
                resp = await self._client.request(method, full_url, headers=req_headers, **kwargs)
                rc = resp.status_code

                # Rate limit -> respect Retry-After and retry
                if rc == 429:
                    retry_after = resp.headers.get("Retry-After")
                    try:
                        sleep_seconds = float(retry_after) if retry_after is not None else 1.0
                    except Exception:
                        sleep_seconds = 1.0
                    await asyncio.sleep(sleep_seconds)
                    continue

                # Authorization problem -> invalidate token and retry once
                if rc == 401:
                    # invalider proprement le token (pas besoin de toucher aux locks)
                    self._token = None
                    self._token_expiry_ts = 0.0
                    await asyncio.sleep(0.5)
                    continue

                # Success path: parse JSON and return
                try:
                    body = resp.json()
                except Exception:
                    # Non-JSON response, treat as text
                    body = {"raw_text": resp.text}

                # Handle errors (4xx/5xx)
                if rc >= 400:
                    if rc < 500:
                        body['error_kind'] = 'ClientError'
                        raise ValueError(body)
                    else:
                        body['error_kind'] = 'ServerError'
                        raise ValueError(body)
                
                msg = (
                    f"Success {rc}\n"
                    f"{method}\n{full_url}\n"
                    f"---\n{kwargs.get('data') or kwargs.get('json') or ''}\n---\n"
                )
                return True, str(msg), body

            except Exception as e:
                if attempts >= 3:
                    error_msg = (
                        f"Request error after {attempts} attempt(s) for\n"
                        f"{method}\n{full_url}\n"
                        f"---\n{kwargs.get('data') or kwargs.get('json') or ''}\n---\n"
                    )
                    try:
                        return False, str(error_msg), e
                    except Exception:
                        return False, str(error_msg), {'error': str(e)}
                await asyncio.sleep(1)
                continue

        # Should not happen
        return False, "Request failed for unknown reason", {}


    async def close(self):
        """Close underlying HTTP client. Call on shutdown if desired."""
        await self._client.aclose()


# ---------------------
# Sync wrapper for AsyncIntraAPI
# ---------------------
# Shared singleton instance of AsyncIntraAPI
_async_api_singleton = AsyncIntraAPI(
    client_id=oauth_secrets.get("oauth_uid"),
    client_secret=oauth_secrets.get("oauth_secret"),
    api_url="https://api.intra.42.fr"
)

class IntraAPI():
    """
    Synchronous wrapper around AsyncIntraAPI for use in sync contexts.
    Uses asgiref.sync.async_to_sync to call async methods.
    """
    def __init__(self, client_id: str = None, client_secret: str = None, api_url: str = "https://api.intra.42.fr"):
        # Tous les wrappers partagent la même AsyncIntraAPI
        self._async_api = _async_api_singleton

    def request(self, method: str, url: str, headers: dict = None, **kwargs) -> tuple[bool, str, dict]:
        """
        Make an authenticated HTTP request to the Intra API.
        This is a synchronous wrapper around AsyncIntraAPI.request using async_to_sync.
        
        Returns (success: bool, response: str, body: dict)

        args:
         - method: HTTP method (GET, POST, etc)
         - url: subPath (e.g. '/v2/users/me' will result to 'https://api.intra.42.fr/v2/users/me')
         - headers: optional dict of HTTP headers
         - **kwargs: additional arguments passed to httpx request (e.g. json=..., data=..., params=...)
            - For a POST, passing payload as 'data=<dict>' works well.
        """
        try:
            return async_to_sync(self._async_api.request)(method, url, headers, **kwargs)
        except Exception as e:
            return False, str(e), {}


# ---------------------
# Export single instance
# ---------------------
intra_api = IntraAPI(
    client_id=oauth_secrets.get("oauth_uid"),
    client_secret=oauth_secrets.get("oauth_secret"),
    api_url="https://api.intra.42.fr"
)
