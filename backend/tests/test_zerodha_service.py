"""
Phase 16 (BYOK) -- ZerodhaService reworked onto per-user credentials.
No prior test coverage existed for this file (Phase 15.1 only covered
BrokerService's generic connect/disconnect state, never the OAuth/Vault
flow) -- this is new coverage, not a preserved regression suite.
"""
import time
from uuid import uuid4

import pytest
from kiteconnect import KiteConnect

from app.core.oauth_state import sign_state, verify_state
from app.services.zerodha_service import ZerodhaService
from tests.fakes import FakeBrokerConnectionRepository, FakeVaultRepository


def make_service(repo=None, vault=None):
    return ZerodhaService(
        broker_connection_repository=repo or FakeBrokerConnectionRepository(),
        vault_repository=vault or FakeVaultRepository(),
        trade_service=None,
        instrument_repository=None,
    )


# --- oauth_state.py: sign/verify, used directly by the callback flow ---

def test_verify_state_accepts_freshly_signed_token():
    user_id = uuid4()
    state = sign_state(user_id)
    assert verify_state(state) == user_id


def test_verify_state_rejects_tampered_signature():
    user_id = uuid4()
    state = sign_state(user_id)
    payload, signature = state.rsplit(":", 1)
    tampered = f"{payload}:{'0' * len(signature)}"
    with pytest.raises(ValueError, match="Invalid state parameter signature"):
        verify_state(tampered)


def test_verify_state_rejects_expired_token():
    # Craft an already-expired-but-correctly-signed token directly, rather
    # than sleeping in a test: same signing path as sign_state(), just with
    # an expiry in the past.
    import hashlib
    import hmac as hmac_module
    from app.core.config import settings

    user_id = uuid4()
    expired_at = int(time.time()) - 10
    payload = f"{user_id}:{expired_at}"
    signature = hmac_module.new(
        settings.OAUTH_STATE_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    expired_state = f"{payload}:{signature}"

    with pytest.raises(ValueError, match="expired"):
        verify_state(expired_state)


def test_verify_state_rejects_malformed_token():
    with pytest.raises(ValueError, match="Malformed"):
        verify_state("not-a-valid-state-token")


def test_verify_state_rejects_state_signed_for_different_user_id_string():
    """A state token is only valid for the exact payload it was signed
    over -- editing the user_id after signing must invalidate it."""
    real_user = uuid4()
    other_user = uuid4()
    state = sign_state(real_user)
    _, expires_at, signature = state.split(":")
    forged = f"{other_user}:{expires_at}:{signature}"
    with pytest.raises(ValueError, match="Invalid state parameter signature"):
        verify_state(forged)


# --- get_login_url ---

def test_get_login_url_requires_submitted_api_key():
    service = make_service()
    with pytest.raises(ValueError, match="No Zerodha API key on file"):
        service.get_login_url(uuid4())


def test_get_login_url_uses_connection_api_key_and_embeds_signed_state():
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    repo.create_connection(user_id=user_id, broker_name="zerodha", api_key="my-kite-key")
    service = make_service(repo=repo)

    url = service.get_login_url(user_id)

    assert "api_key=my-kite-key" in url
    assert "redirect_params=" in url
    # redirect_params is URL-encoded "state=<token>" -- decode and verify
    # round-trips back to this exact user_id.
    from urllib.parse import unquote, parse_qs, urlparse
    query = parse_qs(urlparse(url).query)
    embedded = unquote(query["redirect_params"][0])
    assert embedded.startswith("state=")
    embedded_state = embedded[len("state="):]
    assert verify_state(embedded_state) == user_id


# --- handle_callback ---

def test_handle_callback_rejects_invalid_state():
    service = make_service()
    with pytest.raises(ValueError, match="Invalid or expired login session"):
        service.handle_callback(state="garbage", request_token="tok")


def test_handle_callback_requires_credentials_submitted_first():
    user_id = uuid4()
    state = sign_state(user_id)
    service = make_service()  # no connection at all
    with pytest.raises(ValueError, match="No Zerodha credentials found"):
        service.handle_callback(state=state, request_token="tok")


def test_handle_callback_requires_api_secret_not_just_api_key():
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    repo.create_connection(user_id=user_id, broker_name="zerodha", api_key="key-only")
    service = make_service(repo=repo)
    state = sign_state(user_id)

    with pytest.raises(ValueError, match="No Zerodha credentials found"):
        service.handle_callback(state=state, request_token="tok")


def test_handle_callback_exchanges_token_and_stores_in_vault(monkeypatch):
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()
    secret_id = vault.create_secret("my-api-secret", name="x")
    conn = repo.create_connection(
        user_id=user_id, broker_name="zerodha", api_key="my-key",
        api_secret_kms_id=str(secret_id),
    )
    conn.status = "disconnected"  # simulate a reconnect
    service = make_service(repo=repo, vault=vault)
    state = sign_state(user_id)

    captured = {}

    def fake_generate_session(self, request_token, api_secret):
        captured["request_token"] = request_token
        captured["api_secret"] = api_secret
        return {"access_token": "brand-new-access-token"}

    monkeypatch.setattr(KiteConnect, "generate_session", fake_generate_session)

    result = service.handle_callback(state=state, request_token="req-tok-123")

    assert captured["request_token"] == "req-tok-123"
    assert captured["api_secret"] == "my-api-secret"  # pulled from Vault, not a global env var
    assert result.status == "active"  # reconnect flips it back to active
    assert result.access_token_kms_id is not None
    from uuid import UUID
    assert vault.get_secret(UUID(result.access_token_kms_id)) == "brand-new-access-token"


def test_handle_callback_wraps_kite_exchange_failure(monkeypatch):
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()
    secret_id = vault.create_secret("my-api-secret", name="x")
    repo.create_connection(
        user_id=user_id, broker_name="zerodha", api_key="my-key",
        api_secret_kms_id=str(secret_id),
    )
    service = make_service(repo=repo, vault=vault)
    state = sign_state(user_id)

    def failing_generate_session(self, request_token, api_secret):
        raise Exception("Token is invalid or has expired.")

    monkeypatch.setattr(KiteConnect, "generate_session", failing_generate_session)

    with pytest.raises(ValueError, match="Failed to exchange request token"):
        service.handle_callback(state=state, request_token="not-a-real-token")


# --- get_access_token ---

def test_get_access_token_requires_a_connection():
    service = make_service()
    with pytest.raises(ValueError, match="No Zerodha access token found"):
        service.get_access_token(uuid4())


def test_get_access_token_returns_stored_token():
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()
    secret_id = vault.create_secret("stored-token", name="x")
    repo.create_connection(user_id=user_id, broker_name="zerodha", api_key="key")
    conn = repo.get_by_user_and_broker(user_id, "zerodha")
    repo.update_access_token_kms_id(conn, str(secret_id))
    service = make_service(repo=repo, vault=vault)

    assert service.get_access_token(user_id) == "stored-token"
