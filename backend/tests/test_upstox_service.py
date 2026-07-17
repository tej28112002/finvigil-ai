"""
Phase 16 (BYOK) -- UpstoxService, following the same OAuth-redirect pattern
as ZerodhaService (see test_zerodha_service.py) but exchanging the
authorization code via plain `requests` calls instead of the kiteconnect
SDK, since Upstox has no official Python SDK used elsewhere in this repo.
"""
from uuid import uuid4

import pytest
import requests

from app.core.oauth_state import sign_state, verify_state
from app.services.upstox_service import UpstoxService
from tests.fakes import FakeBrokerConnectionRepository, FakeVaultRepository


def make_service(repo=None, vault=None):
    return UpstoxService(
        broker_connection_repository=repo or FakeBrokerConnectionRepository(),
        vault_repository=vault or FakeVaultRepository(),
        trade_service=None,
        instrument_repository=None,
    )


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


# --- get_login_url ---

def test_get_login_url_requires_submitted_api_key():
    service = make_service()
    with pytest.raises(ValueError, match="No Upstox API key on file"):
        service.get_login_url(uuid4())


def test_get_login_url_uses_connection_api_key_and_embeds_signed_state():
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    repo.create_connection(user_id=user_id, broker_name="upstox", api_key="my-client-id")
    service = make_service(repo=repo)

    url = service.get_login_url(user_id)

    assert "client_id=my-client-id" in url
    assert "response_type=code" in url

    from urllib.parse import parse_qs, urlparse
    query = parse_qs(urlparse(url).query)
    assert verify_state(query["state"][0]) == user_id
    assert query["redirect_uri"][0].endswith("/brokers/upstox/callback")


# --- handle_callback ---

def test_handle_callback_rejects_invalid_state():
    service = make_service()
    with pytest.raises(ValueError, match="Invalid or expired login session"):
        service.handle_callback(state="garbage", code="abc")


def test_handle_callback_requires_credentials_submitted_first():
    user_id = uuid4()
    state = sign_state(user_id)
    service = make_service()  # no connection at all
    with pytest.raises(ValueError, match="No Upstox credentials found"):
        service.handle_callback(state=state, code="abc")


def test_handle_callback_requires_api_secret_not_just_api_key():
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    repo.create_connection(user_id=user_id, broker_name="upstox", api_key="key-only")
    service = make_service(repo=repo)
    state = sign_state(user_id)

    with pytest.raises(ValueError, match="No Upstox credentials found"):
        service.handle_callback(state=state, code="abc")


def test_handle_callback_exchanges_code_and_stores_in_vault(monkeypatch):
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()
    secret_id = vault.create_secret("my-client-secret", name="x")
    conn = repo.create_connection(
        user_id=user_id, broker_name="upstox", api_key="my-client-id",
        api_secret_kms_id=str(secret_id),
    )
    conn.status = "disconnected"  # simulate a reconnect
    service = make_service(repo=repo, vault=vault)
    state = sign_state(user_id)

    captured = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return FakeResponse({"access_token": "brand-new-access-token"})

    monkeypatch.setattr(requests, "post", fake_post)

    result = service.handle_callback(state=state, code="auth-code-123")

    assert captured["data"]["code"] == "auth-code-123"
    assert captured["data"]["client_id"] == "my-client-id"
    assert captured["data"]["client_secret"] == "my-client-secret"  # pulled from Vault
    assert captured["data"]["grant_type"] == "authorization_code"
    assert result.status == "active"  # reconnect flips it back to active
    assert result.access_token_kms_id is not None
    from uuid import UUID
    assert vault.get_secret(UUID(result.access_token_kms_id)) == "brand-new-access-token"


def test_handle_callback_wraps_token_exchange_failure(monkeypatch):
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()
    secret_id = vault.create_secret("my-client-secret", name="x")
    repo.create_connection(
        user_id=user_id, broker_name="upstox", api_key="my-client-id",
        api_secret_kms_id=str(secret_id),
    )
    service = make_service(repo=repo, vault=vault)
    state = sign_state(user_id)

    def failing_post(url, data=None, headers=None, timeout=None):
        return FakeResponse({"error": "invalid_grant"}, status_code=400)

    monkeypatch.setattr(requests, "post", failing_post)

    with pytest.raises(ValueError, match="Failed to exchange authorization code"):
        service.handle_callback(state=state, code="not-a-real-code")


# --- get_access_token ---

def test_get_access_token_requires_a_connection():
    service = make_service()
    with pytest.raises(ValueError, match="No Upstox access token found"):
        service.get_access_token(uuid4())


def test_get_access_token_returns_stored_token():
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()
    secret_id = vault.create_secret("stored-token", name="x")
    repo.create_connection(user_id=user_id, broker_name="upstox", api_key="key")
    conn = repo.get_by_user_and_broker(user_id, "upstox")
    repo.update_access_token_kms_id(conn, str(secret_id))
    service = make_service(repo=repo, vault=vault)

    assert service.get_access_token(user_id) == "stored-token"
