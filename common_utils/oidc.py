import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from helusers.oidc import ApiTokenAuthentication
from oauthlib.oauth2 import OAuth2Error
from requests_oauthlib import OAuth2Session

from common_utils.exceptions import TokenExchangeError


class GraphQLApiTokenAuthentication(ApiTokenAuthentication):
    """
    Custom wrapper for the helusers.oidc.ApiTokenAuthentication backend.
    Needed to make it work with graphql_jwt.middleware.JSONWebTokenMiddleware,
    which in turn calls django.contrib.auth.middleware.AuthenticationMiddleware.

    Authenticate function should:
    1. accept kwargs, or django's auth middleware will not call it
    2. return only the user object, or django's auth middleware will fail
    """

    def authenticate(self, request, **kwargs):
        user_auth_tuple = super().authenticate(request)
        if not user_auth_tuple:
            return None
        user, auth = user_auth_tuple
        return user


class TunnistamoTokenExchange:
    """Exchanges an authorization code with Tunnistamo into API token for open-city-profile."""

    timeout = 5

    def __init__(self):
        self.check_settings()

        self.oidc_endpoint = settings.SOCIAL_AUTH_TUNNISTAMO_OIDC_ENDPOINT
        self.client_id = settings.SOCIAL_AUTH_TUNNISTAMO_KEY
        self.client_secret = settings.SOCIAL_AUTH_TUNNISTAMO_SECRET

        self.scope = settings.HELSINKI_PROFILE_AUTH_SCOPE
        self.callback_url = settings.HELSINKI_PROFILE_AUTH_CALLBACK_URL

    @staticmethod
    def check_settings():
        if not (
            settings.SOCIAL_AUTH_TUNNISTAMO_OIDC_ENDPOINT
            and settings.SOCIAL_AUTH_TUNNISTAMO_KEY
            and settings.SOCIAL_AUTH_TUNNISTAMO_SECRET
        ):
            raise ImproperlyConfigured("Required OAuth/OIDC configuration not set.")

        if not (
            settings.HELSINKI_PROFILE_AUTH_SCOPE
            and settings.HELSINKI_PROFILE_AUTH_CALLBACK_URL
        ):
            raise ImproperlyConfigured(
                "Required Helsinki profile configuration not set."
            )

    def fetch_api_token(self, authorization_code: str) -> str:
        """Exchanges the authorization code into a API token that can access open-city-profile API."""
        oidc_conf = self.get_oidc_config()

        try:
            session = OAuth2Session(
                client_id=self.client_id,
                redirect_uri=self.callback_url,
                scope=f"openid {self.scope}",
            )
            authorization_url, state = session.authorization_url(
                oidc_conf["authorization_endpoint"]
            )
            redirect_response = (
                f"{self.callback_url}?code={authorization_code}&state={state}"
            )
            session.fetch_token(
                token_url=oidc_conf["token_endpoint"],
                authorization_response=redirect_response,
                client_secret=self.client_secret,
                include_client_id=True,
                timeout=self.timeout,
            )
        except OAuth2Error as exc:
            raise TokenExchangeError("Failed to obtain an access token.") from exc

        response = session.get(self.oidc_endpoint + "/api-tokens", timeout=self.timeout)
        response.raise_for_status()

        api_tokens = response.json()

        if self.scope in api_tokens:
            return api_tokens[self.scope]

        raise TokenExchangeError(
            f"Token for scope {self.scope} not available in response."
        )

    def get_authorization_token_url(self):
        """Return the url, which will generate a authorization code when visited."""
        oidc_conf = self.get_oidc_config()
        session = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.callback_url,
            scope=f"openid {self.scope}",
        )

        authorization_url, state = session.authorization_url(
            oidc_conf["authorization_endpoint"]
        )
        return authorization_url

    def get_oidc_config(self):
        return self.get(self.oidc_endpoint + "/.well-known/openid-configuration").json()

    def get(self, url: str) -> requests.Response:
        headers = {"accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response
