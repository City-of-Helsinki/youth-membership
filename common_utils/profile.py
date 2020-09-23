import jmespath
import requests
from django.conf import settings
from requests.auth import AuthBase

from common_utils.oidc import TunnistamoTokenExchange


class BearerAuth(AuthBase):
    """Bearer token authentication module for requests."""

    def __init__(self, token: str):
        self.token = token

    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r


class ProfileAPI:
    """Client for fetching open-city-profile related data."""

    MY_PROFILE_QUERY = """
        query myProfile {
            myProfile {
                id
            }
        }
    """

    MY_PROFILE_PATH = jmespath.compile(
        """
        data.myProfile.{
            id: id
        }
    """
    )

    def __init__(self):
        self.api_url = settings.HELSINKI_PROFILE_API_URL
        self.timeout = 5

    def fetch_my_profile(self, authorization_code: str) -> dict:
        """Fetch profile data for the user of the given authorization code."""
        token_exchange = TunnistamoTokenExchange()
        api_token = token_exchange.fetch_api_token(authorization_code)
        response = requests.post(
            self.api_url,
            json={"query": self.MY_PROFILE_QUERY},
            timeout=self.timeout,
            auth=BearerAuth(api_token),
        )
        response.raise_for_status()

        data = response.json()
        return self.MY_PROFILE_PATH.search(data)
