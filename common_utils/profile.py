import jmespath
import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
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

    timeout = 5

    def __init__(self):
        self.check_settings()

    @staticmethod
    def check_settings():
        if not settings.HELSINKI_PROFILE_API_URL:
            raise ImproperlyConfigured(
                "Required Helsinki profile configuration not set."
            )

    def fetch_my_profile(self, authorization_code: str) -> dict:
        """Fetch profile data for the user of the given authorization code."""
        query = """
            query myProfile {
                myProfile {
                    id
                }
            }
        """
        path = jmespath.compile(
            """
            data.myProfile.{
                id: id
            }
        """
        )

        data = self.do_query(authorization_code, query)
        return path.search(data)

    def do_query(self, authorization_code: str, query: str) -> dict:
        token_exchange = TunnistamoTokenExchange()
        api_token = token_exchange.fetch_api_token(authorization_code)
        response = requests.post(
            settings.HELSINKI_PROFILE_API_URL,
            json={"query": query},
            timeout=self.timeout,
            auth=BearerAuth(api_token),
        )
        response.raise_for_status()

        return response.json()
