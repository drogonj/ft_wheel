from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
import time, os

from custom_auth.views import oauth_secrets

# Call 42 API
# Essentialy for jackpots, not for Authentification
class IntraAPI:
    def __init__(self):
        self.token = None
        self.token_created_at = None
        self.token_expire_in = None

        self.api_url = 'https://api.intra.42.fr/v2'


    def get_token(self):
        """
        Get a valid OAuth2 token for the 42 API.
        If a valid token is already available, it will be returned.
        If not, a new token will be fetched.
        Returns:
            dict: The OAuth2 token containing access token and other details.
        """
        # Check if we have a valid token
        if self.token and self.token_created_at and self.token_expire_in:
            current_time = int(time.time())
            if current_time < self.token_created_at + self.token_expire_in:
                print(f"Using existing token {self.token['access_token']}")
                return self.token


        # If no valid token, fetch a new one
        try:
            client = BackendApplicationClient(client_id=oauth_secrets['oauth_uid'])
            oauth = OAuth2Session(client=client)
            token = oauth.fetch_token(
                token_url='https://api.intra.42.fr/oauth/token',
                client_id=oauth_secrets['oauth_uid'],
                client_secret=oauth_secrets['oauth_secret'],
            )
            self.token = token
            self.token_created_at = token['created_at']
            self.token_expire_in = token['expires_in']
            return token
        except Exception as e:
            print(f"Error fetching token: {e}")
            self.intra_logger("ERROR", f"Error fetching token: {e}")
            return None
   

    def request(self, method, url, headers=None, **kwargs):
        """
        Makes an authenticated request to the 42 API using the given method and URL.
        Args:
            method (str): The HTTP method to use (e.g., 'GET', 'POST').
            url (str): The URL to make the request to.
            headers (dict): Additional headers to include in the request.
            **kwargs: Additional arguments to pass to the request method.
        Returns:
            dict: The JSON response from the API if successful, None otherwise.
        """

        if not url.startswith('http'):
            url = self.api_url + url

        attempts = 0
        while (attempts < 3):
            rc = None
            attempts += 1
            try:
                client = BackendApplicationClient(client_id=oauth_secrets['oauth_uid'])
                oauth = OAuth2Session(client=client, token=self.get_token())
                response = oauth.request(method, url, headers=headers, **kwargs)
                rc = response.status_code

                if rc == 429:
                    time.sleep(float(response.headers['Retry-After']))
                    continue
                if rc >= 400:
                    if rc < 500:
                        raise ValueError(f"\n{response.headers}\n\nClientError. Error {str(rc)}\n{str(response.content)}\n")
                    else:
                        raise ValueError(f"\n{response.headers}\n\nServerError. Error {str(rc)}\n{str(response.content)}\n")
                self.intra_logger(
                    "INFO",
                    f"{response.json()} with request: {method} {url} {headers} {kwargs}"
                )
                return response.json()
            
            except Exception as e:
                print(f"Error making {method} request to {url} - attempts: {attempts} - error: {e}")
                if attempts >= 3:
                    print(f"Failed to make {method} request to {url} after {attempts} attempts.")
                    self.intra_logger("ERROR", f"Failed to make {method} request to {url} after {attempts} attempts. Error: {e}")
                    raise e
                time.sleep(1)


    def intra_logger(self, kind, message):
        """
        Write logs for IntraAPI actions in /var/log/ft_wheel/intra_{kind}.log
        Args:
            kind (str): The kind of log (e.g., 'INFO', 'ERROR').
            message (str): The log message.
        """
        log_file = f"/var/log/ft_wheel/intra_{kind.lower()}.log"
        try:
            # Directory should already exist from Dockerfile, but create if needed
            os.makedirs("/var/log/ft_wheel/", exist_ok=True)

            # Remove first 1MB if file is larger than 10MB
            if os.path.exists(log_file):
                file_size = os.path.getsize(log_file)
                if file_size > 10485760:  # 10 MB
                    # Remove 1MB from the start of the file
                    with open(log_file, "r+", encoding="utf-8") as f:
                        f.seek(1048576)
                        data = f.read()
                        f.seek(0)
                        f.write(data)
                        f.truncate()

            # Append the log message
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n\n")
        except Exception as e:
            print(f"Error writing log to {log_file}: {e}")



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
        


intra_api = IntraAPI()
