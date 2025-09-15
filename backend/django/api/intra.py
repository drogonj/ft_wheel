from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
import time

from custom_auth.views import oauth_secrets

# Call 42 API
# Essentialy for jackpots, not for Authentification
class IntraAPI:
    def __init__(self):
        self.token = None
        self.token_created_at = None
        self.token_expire_in = None


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
        print("Fetching new token...")
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
            return None
        

    def get(self, url):
        """
        Fetches data from the given URL using the 42 API with OAuth2 authentication.
        Args:
            url (str): The URL to fetch data from.
        Returns:
            dict: The JSON response from the API if successful, None otherwise.
        """
        try:
            client = BackendApplicationClient(client_id=oauth_secrets['oauth_uid'])
            oauth = OAuth2Session(client=client, token=self.get_token())
            response = oauth.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()
        except Exception as e:
            print(f"Error fetching data from {url}: {e}")
            return None


    def get_user_coa(self, login, fields=None):
        """
        Fetches the coalitions data for a user from the 42 API by login.
        Args:
            login (str): The login of the user.
            fields (list, optional): List of fields to return from the coalition data.
                                     If None, returns all fields.
        """
        url = f'https://api.intra.42.fr/v2/users/{login}/coalitions'
        response = self.get(url)

        if response and len(response) > 0:
            if fields:
                return [{field: coalition.get(field) for field in fields if field in coalition} for coalition in response]
            return response
        else:
            print(f"Coalition data for user with login '{login}' not found.")
            return None 
        


intra_api = IntraAPI()
