from unittest.mock import MagicMock

import pytest
from requests_oauthlib import OAuth2Session

from common_utils.oidc import TunnistamoTokenExchange


def mock_token_exchange(mocker, token_response):
    response = MagicMock()
    response.json.return_value = token_response
    mocker.patch.object(TunnistamoTokenExchange, "get_oidc_config")
    mocker.patch.object(
        OAuth2Session, "authorization_url", return_value=("url", "state")
    )
    mocker.patch.object(OAuth2Session, "fetch_token")
    mocker.patch.object(OAuth2Session, "get", return_value=response)


def test_authorization_code_exchange_correct_scope_in_response(mocker):
    tte = TunnistamoTokenExchange()
    token_response = {tte.scope: "code"}
    mock_token_exchange(mocker, token_response)
    api_token = tte.fetch_api_token("auth_code")

    assert api_token == "code"


def test_authorization_code_wrong_scope_in_response(mocker):
    tte = TunnistamoTokenExchange()
    token_response = {tte.scope + "nope": "code"}
    mock_token_exchange(mocker, token_response)

    with pytest.raises(Exception) as e:
        tte.fetch_api_token("auth_code")

    assert "Token for scope" in str(e.value)
