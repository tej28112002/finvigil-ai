"""
Broker connection logic (Phase 15.1 continuation, priority #6) --
BrokerService: connection state transitions and duplicate-broker
prevention.
"""
from uuid import uuid4

import pytest

from app.services.broker_service import BrokerService
from tests.fakes import FakeBrokerConnection, FakeBrokerConnectionRepository


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
