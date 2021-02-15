import datetime

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from helusers.settings import api_token_auth_settings
from jose import jwt

from youths.models import YouthProfile

from .keys import rsa_key

User = get_user_model()

TRUE_VALUES = ["true", "True", "TRUE", "1", 1, True]
FALSE_VALUES = ["false", "False", "FALSE", "0", 0, False]


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


def test_disabled_gdpr_api_responds_with_404(
    api_client, youth_profile, requests_mock, settings
):
    auth_header = get_api_token_for_user_with_scopes(
        youth_profile.user, [settings.GDPR_API_QUERY_SCOPE], requests_mock
    )
    api_client.credentials(HTTP_AUTHORIZATION=auth_header)
    settings.GDPR_API_ENABLED = False
    response = api_client.get(reverse("youths:gdpr", kwargs={"pk": youth_profile.id}))
    assert response.status_code == 404

    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.id})
    )
    assert response.status_code == 404


def test_get_profile_information_from_gdpr_api(
    api_client, youth_profile, snapshot, requests_mock, settings
):
    auth_header = get_api_token_for_user_with_scopes(
        youth_profile.user, [settings.GDPR_API_QUERY_SCOPE], requests_mock
    )
    api_client.credentials(HTTP_AUTHORIZATION=auth_header)
    response = api_client.get(reverse("youths:gdpr", kwargs={"pk": youth_profile.id}))

    assert response.status_code == 200
    snapshot.assert_match(response.json())


@pytest.mark.parametrize("true_value", TRUE_VALUES)
def test_delete_profile_dry_run_data(
    true_value, api_client, youth_profile, requests_mock, settings
):
    auth_header = get_api_token_for_user_with_scopes(
        youth_profile.user, [settings.GDPR_API_DELETE_SCOPE], requests_mock
    )
    api_client.credentials(HTTP_AUTHORIZATION=auth_header)
    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.id}),
        data={"dry_run": true_value},
        format="json",
    )

    assert response.status_code == 204
    assert YouthProfile.objects.count() == 1
    assert User.objects.count() == 1


@pytest.mark.parametrize("true_value", TRUE_VALUES)
def test_delete_profile_dry_run_query_params(
    true_value, api_client, youth_profile, requests_mock, settings
):
    auth_header = get_api_token_for_user_with_scopes(
        youth_profile.user, [settings.GDPR_API_DELETE_SCOPE], requests_mock
    )
    api_client.credentials(HTTP_AUTHORIZATION=auth_header)
    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.id})
        + f"?dry_run={true_value}",
    )

    assert response.status_code == 204
    assert YouthProfile.objects.count() == 1
    assert User.objects.count() == 1


def test_delete_profile(api_client, youth_profile, requests_mock, settings):
    auth_header = get_api_token_for_user_with_scopes(
        youth_profile.user, [settings.GDPR_API_DELETE_SCOPE], requests_mock
    )
    api_client.credentials(HTTP_AUTHORIZATION=auth_header)
    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.id})
    )

    assert response.status_code == 204
    assert YouthProfile.objects.count() == 0
    assert User.objects.count() == 0


@pytest.mark.parametrize("false_value", FALSE_VALUES)
def test_delete_profile_dry_run_query_params_false(
    false_value, api_client, youth_profile, requests_mock, settings
):
    auth_header = get_api_token_for_user_with_scopes(
        youth_profile.user, [settings.GDPR_API_DELETE_SCOPE], requests_mock
    )
    api_client.credentials(HTTP_AUTHORIZATION=auth_header)
    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.id})
        + f"?dry_run={false_value}",
    )

    assert response.status_code == 204
    assert YouthProfile.objects.count() == 0
    assert User.objects.count() == 0


@pytest.mark.parametrize("false_value", FALSE_VALUES)
def test_delete_profile_dry_run_data_false(
    false_value, api_client, youth_profile, requests_mock, settings
):
    auth_header = get_api_token_for_user_with_scopes(
        youth_profile.user, [settings.GDPR_API_DELETE_SCOPE], requests_mock
    )
    api_client.credentials(HTTP_AUTHORIZATION=auth_header)
    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.id}),
        data={"dry_run": false_value},
        format="json",
    )

    assert response.status_code == 204
    assert YouthProfile.objects.count() == 0
    assert User.objects.count() == 0


def test_gdpr_api_requires_authentication(api_client, youth_profile, snapshot):
    response = api_client.get(reverse("youths:gdpr", kwargs={"pk": youth_profile.id}))
    assert response.status_code == 401

    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.id})
    )
    assert response.status_code == 401


def test_user_can_only_access_his_own_profile(
    api_client, user, youth_profile, requests_mock, settings
):
    auth_header = get_api_token_for_user_with_scopes(
        user,
        [settings.GDPR_API_QUERY_SCOPE, settings.GDPR_API_DELETE_SCOPE],
        requests_mock,
    )
    api_client.credentials(HTTP_AUTHORIZATION=auth_header)

    response = api_client.get(reverse("youths:gdpr", kwargs={"pk": youth_profile.id}))
    assert response.status_code == 403

    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.id})
    )
    assert response.status_code == 403


@pytest.mark.parametrize("use_correct_scope", [True, False])
def test_gdpr_query_requires_correct_scope(
    use_correct_scope, api_client, youth_profile, requests_mock, settings
):
    if use_correct_scope:
        auth_header = get_api_token_for_user_with_scopes(
            youth_profile.user,
            [settings.GDPR_API_QUERY_SCOPE, settings.GDPR_API_DELETE_SCOPE],
            requests_mock,
        )
    else:
        auth_header = get_api_token_for_user_with_scopes(
            youth_profile.user, [settings.GDPR_API_DELETE_SCOPE], requests_mock
        )
    api_client.credentials(HTTP_AUTHORIZATION=auth_header)

    response = api_client.get(reverse("youths:gdpr", kwargs={"pk": youth_profile.id}))

    if use_correct_scope:
        assert response.status_code == 200
    else:
        assert response.status_code == 403


@pytest.mark.parametrize("use_correct_scope", [True, False])
def test_gdpr_delete_requires_correct_scope(
    use_correct_scope, api_client, youth_profile, requests_mock, settings
):
    if use_correct_scope:
        auth_header = get_api_token_for_user_with_scopes(
            youth_profile.user,
            [settings.GDPR_API_QUERY_SCOPE, settings.GDPR_API_DELETE_SCOPE],
            requests_mock,
        )
    else:
        auth_header = get_api_token_for_user_with_scopes(
            youth_profile.user, [settings.GDPR_API_QUERY_SCOPE], requests_mock
        )
    api_client.credentials(HTTP_AUTHORIZATION=auth_header)

    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.id})
    )

    if use_correct_scope:
        assert response.status_code == 204
    else:
        assert response.status_code == 403
        assert YouthProfile.objects.count() == 1
        assert User.objects.count() == 1
