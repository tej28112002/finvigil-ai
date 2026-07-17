"""
Broker connection logic (Phase 15.1 continuation, priority #6) --
BrokerService: connection state transitions and duplicate-broker
prevention.

Phase 16 (BYOK) addition: submit_credentials() -- api_key stored plain,
api_secret/totp_secret Vault-wrapped, create-or-update semantics.
"""
from uuid import uuid4

import pytest

from app.services.broker_service import BrokerService
from tests.fakes import (
    FakeBrokerConnection,
    FakeBrokerConnectionRepository,
    FakeVaultRepository,
)


def test_connect_broker_rejects_unknown_broker_name():
    service = BrokerService(FakeBrokerConnectionRepository())
    with pytest.raises(ValueError, match="Invalid broker"):
        service.connect_broker(uuid4(), "robinhood")  # not in the supported list


def test_connect_broker_accepts_each_supported_broker():
    for broker in ["zerodha", "groww", "upstox", "wazirx", "coindcx", "csv"]:
        service = BrokerService(FakeBrokerConnectionRepository())
        conn = service.connect_broker(uuid4(), broker)
        assert conn.broker_name == broker
        assert conn.status == "active"


def test_connect_broker_prevents_duplicate_connection():
    """Same user, same broker, connected twice -- second attempt must be
    rejected, not silently create a second row for the same broker."""
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    service = BrokerService(repo)

    service.connect_broker(user_id, "zerodha")
    with pytest.raises(ValueError, match="already connected"):
        service.connect_broker(user_id, "zerodha")

    assert len(repo.get_by_user(user_id)) == 1


def test_connect_broker_allows_same_broker_for_different_users():
    """The duplicate check is scoped per-user -- two different users
    connecting to Zerodha independently must both succeed."""
    repo = FakeBrokerConnectionRepository()
    service = BrokerService(repo)

    service.connect_broker(uuid4(), "zerodha")
    service.connect_broker(uuid4(), "zerodha")  # different user -- must not raise


def test_connect_broker_allows_different_brokers_for_same_user():
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    service = BrokerService(repo)

    service.connect_broker(user_id, "zerodha")
    service.connect_broker(user_id, "upstox")

    assert len(repo.get_by_user(user_id)) == 2


def test_disconnect_broker_sets_status_disconnected():
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    service = BrokerService(repo)
    conn = service.connect_broker(user_id, "zerodha")

    result = service.disconnect_broker(user_id, conn.id)

    assert result.status == "disconnected"


def test_disconnect_broker_not_found_raises():
    service = BrokerService(FakeBrokerConnectionRepository())
    with pytest.raises(ValueError, match="not found"):
        service.disconnect_broker(uuid4(), uuid4())


def test_disconnect_broker_wrong_owner_rejected():
    """Ownership check: user B must not be able to disconnect user A's
    broker connection by guessing/reusing its id."""
    user_a = uuid4()
    user_b = uuid4()
    repo = FakeBrokerConnectionRepository()
    service = BrokerService(repo)
    conn = service.connect_broker(user_a, "zerodha")

    with pytest.raises(ValueError, match="permission"):
        service.disconnect_broker(user_b, conn.id)

    assert conn.status == "active"  # untouched


def test_submit_credentials_rejects_non_byok_broker():
    """Only brokers with a real BYOK flow (Zerodha so far) accept
    submit_credentials -- csv/wazirx/coindcx have no credential intake."""
    service = BrokerService(FakeBrokerConnectionRepository(), FakeVaultRepository())
    with pytest.raises(ValueError, match="not supported"):
        service.submit_credentials(uuid4(), "csv", api_key="x")


def test_submit_credentials_requires_vault_repository():
    service = BrokerService(FakeBrokerConnectionRepository())  # no vault
    with pytest.raises(ValueError, match="Vault repository is required"):
        service.submit_credentials(uuid4(), "zerodha", api_key="x")


def test_submit_credentials_creates_connection_with_plain_api_key():
    """api_key is never Vault-wrapped -- it's a client identifier, not a
    secret (mirrors Kite Connect's own security model)."""
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()
    service = BrokerService(repo, vault)

    conn = service.submit_credentials(
        user_id, "zerodha", api_key="my_kite_key", api_secret="my_kite_secret"
    )

    assert conn.api_key == "my_kite_key"
    assert conn.api_key not in vault.secrets.values()  # never Vault-wrapped


def test_submit_credentials_vault_wraps_api_secret():
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()
    service = BrokerService(repo, vault)

    conn = service.submit_credentials(
        user_id, "zerodha", api_key="key", api_secret="super-secret"
    )

    assert conn.api_secret_kms_id is not None
    from uuid import UUID
    assert vault.get_secret(UUID(conn.api_secret_kms_id)) == "super-secret"


def test_submit_credentials_second_call_updates_existing_connection():
    """Re-submitting credentials (e.g. rotating a Kite Connect app secret)
    updates the same broker_connections row and the same Vault secret --
    doesn't silently create a second connection for the same user+broker."""
    user_id = uuid4()
    repo = FakeBrokerConnectionRepository()
    vault = FakeVaultRepository()
    service = BrokerService(repo, vault)

    first = service.submit_credentials(
        user_id, "zerodha", api_key="key-v1", api_secret="secret-v1"
    )
    second = service.submit_credentials(
        user_id, "zerodha", api_key="key-v2", api_secret="secret-v2"
    )

    assert first.id == second.id
    assert len(repo.get_by_user(user_id)) == 1
    assert second.api_key == "key-v2"
    from uuid import UUID
    assert vault.get_secret(UUID(second.api_secret_kms_id)) == "secret-v2"
    assert second.api_secret_kms_id == first.api_secret_kms_id  # same slot, updated in place


def test_submit_credentials_rejects_missing_api_key():
    service = BrokerService(FakeBrokerConnectionRepository(), FakeVaultRepository())
    with pytest.raises(ValueError, match="api_key is required"):
        service.submit_credentials(uuid4(), "zerodha", api_key="")
