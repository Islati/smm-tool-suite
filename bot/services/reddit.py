import requests
import requests.auth


class RedditClient(object):
    def __init__(self, client_id, client_secret, username, password):
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password

        self.client_auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
        self._oauth_token = None

    def request_oauth_token(self):
        """
        Request an OAuth token from Reddit
        :return:
        """
        post_data = {"grant_type": "password", "username": self.username, "password": self.password}
        headers = {"User-Agent": "VidBot/0.1 by Skreet.ca"}
        response = requests.post("https://www.reddit.com/api/v1/access_token", auth=self.client_auth, data=post_data,
                                 headers=headers)
        response_data = response.json()
        return response_data["access_token"]

    def get_authorization_headers(self):
        if self._oauth_token is None:
            self._oauth_token = self.request_oauth_token()

        return {"Authorization": f"bearer {self._oauth_token}", "User-Agent": "VidBot/0.1 by Skreet.ca"}
