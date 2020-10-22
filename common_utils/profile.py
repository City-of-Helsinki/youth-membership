import jmespath
import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from requests.auth import AuthBase


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

    def fetch_profile(self, api_token: str, id: str) -> dict:
        """Fetch profile data for the given profile ID. Requires staff level permission"""
        query = """
            query Profile($id: ID!, $service_type: ServiceType!) {
                profile(id: $id, serviceType: $service_type) {
                    id
                }
            }
        """

        path = jmespath.compile(
            """
            data.profile.{
                id: id
            }
        """
        )

        data = self.do_query(
            api_token,
            query,
            {"id": id, "service_type": settings.HELSINKI_PROFILE_SERVICE_TYPE},
        )
        return path.search(data)

    def fetch_my_profile(self, api_token: str) -> dict:
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

        data = self.do_query(api_token, query)
        return path.search(data)

    def do_query(self, api_token: str, query: str, variables: dict = None) -> dict:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        response = requests.post(
            settings.HELSINKI_PROFILE_API_URL,
            json=payload,
            timeout=self.timeout,
            auth=BearerAuth(api_token),
        )
        response.raise_for_status()

        return response.json()
