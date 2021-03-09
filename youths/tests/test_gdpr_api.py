import datetime

from django.contrib.auth import get_user_model
from django.urls import reverse
from helusers.settings import api_token_auth_settings
from jose import jwt

from youths.models import YouthProfile

from .keys import rsa_key

User = get_user_model()


def get_api_token_for_user_with_scopes(user, scopes: list, requests_mock):
    """Build a proper auth token with desired scopes."""
    audience = api_token_auth_settings.AUDIENCE
    issuer = api_token_auth_settings.ISSUER
    auth_field = api_token_auth_settings.API_AUTHORIZATION_FIELD
    config_url = f"{issuer}/.well-known/openid-configuration"
    jwks_url = f"{issuer}/jwks"

    configuration = {
        "issuer": issuer,
        "jwks_uri": jwks_url,
    }

    keys = {"keys": [rsa_key.public_key_jwk]}

    now = datetime.datetime.now()
    expire = now + datetime.timedelta(days=14)

    jwt_data = {
        "iss": issuer,
        "aud": audience,
        "sub": str(user.uuid),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        auth_field: scopes,
    }
    encoded_jwt = jwt.encode(
        jwt_data, key=rsa_key.private_key_pem, algorithm=rsa_key.jose_algorithm
    )

    requests_mock.get(config_url, json=configuration)
    requests_mock.get(jwks_url, json=keys)

    auth_header = f"{api_token_auth_settings.AUTH_SCHEME} {encoded_jwt}"

    return auth_header


def test_get_profile_information_from_gdpr_api(
    api_client, youth_profile, snapshot, requests_mock, settings
):
    auth_header = get_api_token_for_user_with_scopes(
        youth_profile.user, [settings.GDPR_API_QUERY_SCOPE], requests_mock
    )
    api_client.credentials(HTTP_AUTHORIZATION=auth_header)
    response = api_client.get(
        reverse("helsinki_gdpr:gdpr_v1", kwargs={"pk": youth_profile.id})
    )

    assert response.status_code == 200
    snapshot.assert_match(response.json())


def test_delete_profile(api_client, youth_profile, requests_mock, settings):
    auth_header = get_api_token_for_user_with_scopes(
        youth_profile.user, [settings.GDPR_API_DELETE_SCOPE], requests_mock
    )
    api_client.credentials(HTTP_AUTHORIZATION=auth_header)
    response = api_client.delete(
        reverse("helsinki_gdpr:gdpr_v1", kwargs={"pk": youth_profile.id})
    )

    assert response.status_code == 204
    assert YouthProfile.objects.count() == 0
    assert User.objects.count() == 0
