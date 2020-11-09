import jmespath
import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.dateparse import parse_datetime
from requests.auth import AuthBase

from common_utils.exceptions import ProfileAPIError


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

    def contains_keys(self, data, keys):
        if not data:
            raise ProfileAPIError("Error in calling the Helsinki profile API.")

        for key in keys:
            if key not in data:
                raise ProfileAPIError(
                    "Required information not available from the Helsinki profile API."
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
            query,
            api_token=api_token,
            variables={
                "id": id,
                "service_type": settings.HELSINKI_PROFILE_SERVICE_TYPE,
            },
        )

        parsed_data = path.search(data)
        self.contains_keys(parsed_data, ["id"])
        return parsed_data

    def fetch_my_profile(self, api_token: str) -> dict:
        """Fetch profile data for the user of the given API token."""
        query = """
            query myProfile {
                myProfile {
                    id
                    firstName
                    lastName
                }
            }
        """
        path = jmespath.compile(
            """
            data.myProfile.{
                id: id
                first_name: firstName
                last_name: lastName
            }
        """
        )

        data = self.do_query(query, api_token=api_token)

        parsed_data = path.search(data)
        self.contains_keys(parsed_data, ["id", "first_name", "last_name"])
        return parsed_data

    def fetch_profile_with_temporary_access_token(self, temporary_token: str):
        """Fetch profile data for the user using the given temporary Helsinki profile token."""
        query = """
            query profileWithAccessToken($token: UUID!) {
                profileWithAccessToken(token: $token) {
                    id
                    firstName
                    lastName
                    primaryEmail {
                        email
                    }
                }
            }
        """
        path = jmespath.compile(
            """
            data.profileWithAccessToken.{
                id: id
                first_name: firstName
                last_name: lastName
                email: primaryEmail.email
            }
        """
        )
        data = self.do_query(query, variables={"token": temporary_token})

        parsed_data = path.search(data)
        self.contains_keys(parsed_data, ["id", "first_name", "last_name", "email"])
        return parsed_data

    def create_temporary_access_token(self, api_token: str) -> dict:
        """Create a temporary profile access token for the user of the given API token."""
        query = """
            mutation CreateToken {
                createMyProfileTemporaryReadAccessToken(input: {}) {
                    temporaryReadAccessToken {
                        token
                        expiresAt
                    }
                }
            }
        """

        path = jmespath.compile(
            """
            data.createMyProfileTemporaryReadAccessToken.temporaryReadAccessToken.{
                token: token
                expires_at: expiresAt
            }
        """
        )
        data = self.do_query(query, api_token=api_token)
        parsed_data = path.search(data)
        self.contains_keys(parsed_data, ["token", "expires_at"])
        parsed_data["expires_at"] = parse_datetime(parsed_data["expires_at"])
        return parsed_data

    def do_query(
        self, query: str, *, variables: dict = None, api_token: str = None
    ) -> dict:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        response = requests.post(
            settings.HELSINKI_PROFILE_API_URL,
            json=payload,
            timeout=self.timeout,
            auth=BearerAuth(api_token) if api_token else None,
            verify=settings.PROFILE_API_VERIFY,
        )
        response.raise_for_status()

        return response.json()
