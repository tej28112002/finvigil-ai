"""
Lightweight in-memory fakes for pure unit tests — no DB, no network, fast.
Each fake duck-types just the repository methods the service under test
actually calls, matching the real repositories' method signatures exactly
(cross-checked against app/repositories/*.py) so a fake passing a test says
something real about the service's logic, not about the fake's own shape.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4


class FakeSavepoint:
    """Mimics the SessionTransaction SQLAlchemy's Session.begin_nested()
    returns -- usable either as a context manager (`with db.begin_nested():`,
    zerodha_service.py/upstox_service.py's pattern) or with explicit
    .commit()/.rollback() calls (groww_service.py/csv_import_service.py/
    trade_upload_service.py's pattern). No-op either way -- fakes have no
    real transaction to roll back."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def commit(self):
        pass

    def rollback(self):
        pass


class FakeDbSession:
    """Stands in for the SQLAlchemy Session repositories expose as `.db`."""

    def begin_nested(self):
        return FakeSavepoint()


@dataclass
class FakeInstrument:
    symbol: str
    isin: str | None = None
    instrument_type: str = "equity"
    id: UUID = field(default_factory=uuid4)


@dataclass
class FakeLot:
    """Stands in for app.models.holding_lot.HoldingLot."""
    quantity_remaining: Decimal
    buy_price: Decimal
    buy_date: datetime
    id: UUID = field(default_factory=uuid4)
    instrument_id: UUID = field(default_factory=uuid4)
    status: str = "open"
    instrument: FakeInstrument | None = None
    quantity_bought: Decimal | None = None


class FakeHoldingLotRepository:
    """
    Matches HoldingLotRepository's method signatures used by
    HoldingLotService.consume_lots_fifo and HarvestingService.
    get_open_lots must be pre-sorted by buy_date ascending by the caller —
    same contract the real repository's ORDER BY buy_date ASC provides.
    """

    def __init__(self, lots: list[FakeLot]):
        self.lots = lots
        self.update_calls: list[tuple] = []

    def get_open_lots(self, user_id, instrument_id) -> list[FakeLot]:
        return self.lots

    def create_lot(
        self,
        user_id,
        broker_connection_id,
        instrument_id,
        source_trade_id,
        quantity_bought,
        remaining_quantity,
        buy_price,
        buy_date,
        status,
    ) -> FakeLot:
        lot = FakeLot(
            quantity_remaining=remaining_quantity,
            buy_price=buy_price,
            buy_date=buy_date,
            instrument_id=instrument_id,
            status=status,
            quantity_bought=quantity_bought,
        )
        self.lots.append(lot)
        return lot

    def get_active_lots_by_user(self, user_id) -> list[FakeLot]:
        return self.lots

    def get_by_user(self, user_id) -> list[FakeLot]:
        return self.lots

    def get_open_lots_before_date(self, user_id, instrument_id, before_date) -> list[FakeLot]:
        return [lot for lot in self.lots if lot.buy_date < before_date]

    def update_remaining_quantity(self, lot: FakeLot, remaining_quantity, status):
        lot.quantity_remaining = remaining_quantity
        lot.status = status
        self.update_calls.append((lot.id, remaining_quantity, status))
        return lot

    def apply_corporate_action_to_lot(self, lot: FakeLot, new_quantity_bought, new_quantity_remaining, new_buy_price):
        lot.quantity_bought = new_quantity_bought
        lot.quantity_remaining = new_quantity_remaining
        lot.buy_price = new_buy_price
        return lot


@dataclass
class FakeTrade:
    """Stands in for app.models.trade.Trade."""
    idempotency_hash: str
    trade_type: str = "buy"
    quantity: Decimal = Decimal("0")
    price: Decimal = Decimal("0")
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    instrument_id: UUID = field(default_factory=uuid4)
    broker_connection_id: UUID = field(default_factory=uuid4)
    broker_trade_id: str = ""
    execution_time: datetime | None = None


class FakeTradeRepository:
    def __init__(self, trades: list[FakeTrade] | None = None):
        self.trades = trades or []

    def get_by_user(self, user_id) -> list[FakeTrade]:
        return self.trades

    def create_trade(self, **kwargs) -> FakeTrade:
        trade = FakeTrade(
            idempotency_hash=kwargs["idempotency_hash"],
            trade_type=kwargs.get("trade_type", "buy"),
            quantity=kwargs.get("quantity", Decimal("0")),
            price=kwargs.get("price", Decimal("0")),
            user_id=kwargs.get("user_id", uuid4()),
            instrument_id=kwargs.get("instrument_id", uuid4()),
            broker_connection_id=kwargs.get("broker_connection_id", uuid4()),
            broker_trade_id=kwargs.get("broker_trade_id", ""),
            execution_time=kwargs.get("execution_time"),
        )
        self.trades.append(trade)
        return trade


@dataclass
class FakeGain:
    """
    Stands in for app.models.realized_gain.RealizedGain. income_type
    defaults to "equity_capital_gains" -- what every pre-existing
    tax_engine_service.py test already implicitly assumed before this
    field existed -- so those call sites don't need touching. AIS tests
    that need "crypto_vda" or a specific sell_price/quantity_sold set
    them explicitly.
    """
    gain_type: str | None
    profit_loss: Decimal
    income_type: str = "equity_capital_gains"
    sell_price: Decimal = Decimal("0")
    quantity_sold: Decimal = Decimal("0")
    buy_price: Decimal = Decimal("0")
    instrument_id: UUID = field(default_factory=uuid4)
    buy_date: datetime | None = None
    sell_date: datetime | None = None
    holding_days: int = 0


class FakeRealizedGainRepository:
    def __init__(self, gains: list[FakeGain]):
        self.gains = gains

    def get_by_user_income_type_and_date_range(
        self, user_id, income_type, start, end
    ) -> list[FakeGain]:
        # Real filter, not a blanket return-everything: AisMatchingService
        # calls this twice per run (once per category) and needs each call
        # scoped to its own income_type, same as the real repository's
        # SQL WHERE clause.
        return [g for g in self.gains if g.income_type == income_type]

    def get_by_user(self, user_id) -> list[FakeGain]:
        return self.gains


@dataclass
class FakeDashboardProjection:
    """Stands in for app.models.dashboard_projection.DashboardProjection."""
    total_equity_value: Decimal


class FakeDashboardRepository:
    def __init__(self, projection: FakeDashboardProjection | None = None):
        self.projection = projection

    def get_by_user(self, user_id):
        return self.projection


class FakeTaxSummaryRepository:
    """Captures what would have been upserted, without touching the DB."""

    def __init__(self):
        self.upserted: dict | None = None

    def get_by_user_and_year(self, user_id, assessment_year):
        return None

    def upsert_tax_summary(self, **kwargs):
        self.upserted = kwargs
        return SimpleNamespace(**kwargs)


class FakePriceService:
    def __init__(self, prices: dict[str, dict]):
        self.prices = prices

    def get_prices(self, user_id, symbols) -> dict[str, dict]:
        return self.prices


@dataclass
class FakeAisLine:
    """Stands in for app.models.ais_line.AisLine."""
    section_code: str
    reported_amount: Decimal | None
    description: str | None = None
    id: UUID = field(default_factory=uuid4)


class FakeInstrumentRepository:
    def __init__(self, instruments: dict[UUID, FakeInstrument] | None = None):
        self.instruments = instruments or {}
        self.db = FakeDbSession()

    def get_by_id(self, instrument_id):
        return self.instruments.get(instrument_id)

    def get_by_symbol(self, symbol: str) -> FakeInstrument | None:
        return next((i for i in self.instruments.values() if i.symbol == symbol), None)

    def get_by_isin(self, isin: str) -> FakeInstrument | None:
        return next((i for i in self.instruments.values() if i.isin == isin), None)

    def get_or_create(
        self, symbol: str, instrument_type: str, name: str, isin: str | None = None
    ) -> FakeInstrument:
        if isin is not None:
            existing = self.get_by_isin(isin)
            if existing:
                return existing
        existing = self.get_by_symbol(symbol)
        if existing:
            return existing
        instrument = FakeInstrument(symbol=symbol, instrument_type=instrument_type, isin=isin)
        self.instruments[instrument.id] = instrument
        return instrument


class FakeItrSchemaRepository:
    def __init__(self, mapping_record):
        self.mapping_record = mapping_record

    def get_by_ay(self, ay):
        return self.mapping_record


class FakeExistsTaxSummaryRepository:
    """Only the existence check matters to ITR3ExportService.generate_export
    -- it fetches tax_summary but never reads a field from it afterward."""

    def get_by_user_and_year(self, user_id, assessment_year):
        return SimpleNamespace(exists=True)


class FakeCaExportJobRepository:
    def __init__(self):
        self.created: list[dict] = []

    def create_export_job(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(**kwargs)


@dataclass
class FakeSubscription:
    """Stands in for app.models.subscription.Subscription."""
    plan_id: str = "free"
    status: str = "active"
    is_active: bool | None = True
    current_period_end: datetime | None = None
    razorpay_subscription_id: str | None = None
    user_id: UUID = field(default_factory=uuid4)
    id: UUID = field(default_factory=uuid4)


class FakeSubscriptionRepository:
    def __init__(self, subscription: FakeSubscription | None = None):
        self.subscription = subscription
        self.created_default_free = False

    def get_by_user(self, user_id):
        return self.subscription

    def create_default_free(self, user_id):
        self.subscription = FakeSubscription(user_id=user_id, plan_id="free", status="active", is_active=True)
        self.created_default_free = True
        return self.subscription

    def update_status(self, subscription, **kwargs):
        for key, value in kwargs.items():
            if value is not None:
                setattr(subscription, key, value)
        return subscription

    def list_grace_eligible(self):
        if self.subscription and self.subscription.status in ("past_due", "grace"):
            return [self.subscription]
        return []


@dataclass
class FakeBrokerConnection:
    user_id: UUID
    broker_name: str
    status: str = "active"
    id: UUID = field(default_factory=uuid4)
    api_key: str | None = None
    api_secret_kms_id: str | None = None
    access_token_kms_id: str | None = None
    totp_secret_kms_id: str | None = None


class FakeBrokerConnectionRepository:
    def __init__(self, connections: list[FakeBrokerConnection] | None = None):
        self.connections = connections or []

    def get_by_user(self, user_id):
        return [c for c in self.connections if c.user_id == user_id]

    def get_by_user_and_broker(self, user_id, broker_name):
        return next((c for c in self.connections if c.user_id == user_id and c.broker_name == broker_name), None)

    def get_by_id(self, connection_id):
        return next((c for c in self.connections if c.id == connection_id), None)

    def create_connection(self, user_id, broker_name, api_key=None, api_secret_kms_id=None):
        conn = FakeBrokerConnection(
            user_id=user_id,
            broker_name=broker_name,
            api_key=api_key,
            api_secret_kms_id=api_secret_kms_id,
        )
        self.connections.append(conn)
        return conn

    def update_status(self, connection, status):
        connection.status = status
        return connection

    def update_api_key(self, connection, api_key):
        connection.api_key = api_key
        return connection

    def update_api_secret_kms_id(self, connection, api_secret_kms_id):
        connection.api_secret_kms_id = api_secret_kms_id
        return connection

    def update_access_token_kms_id(self, connection, access_token_kms_id):
        connection.access_token_kms_id = access_token_kms_id
        return connection

    def update_totp_secret_kms_id(self, connection, totp_secret_kms_id):
        connection.totp_secret_kms_id = totp_secret_kms_id
        return connection


class FakeVaultRepository:
    """In-memory fake for Supabase Vault (vault.create_secret /
    vault.update_secret / vault.decrypted_secrets), keyed by a fake UUID
    the same way the real VaultRepository is keyed by the real Vault's."""

    def __init__(self):
        self.secrets: dict[UUID, str] = {}

    def create_secret(self, secret_value, name, description=""):
        secret_id = uuid4()
        self.secrets[secret_id] = secret_value
        return secret_id

    def update_secret(self, secret_id, secret_value, name, description=""):
        self.secrets[secret_id] = secret_value

    def get_secret(self, secret_id):
        return self.secrets.get(secret_id)


@dataclass
class FakeJournalEntry:
    user_id: UUID
    transcript: str
    is_deleted: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass
class FakeJournalTag:
    journal_entry_id: UUID
    tag_name: str
    user_id: UUID = field(default_factory=uuid4)
    id: UUID = field(default_factory=uuid4)


class FakeJournalEntryRepository:
    def __init__(self, entries: list[FakeJournalEntry] | None = None):
        self.entries = entries or []

    def create_entry(self, user_id, transcript):
        entry = FakeJournalEntry(user_id=user_id, transcript=transcript)
        self.entries.append(entry)
        return entry

    def get_by_id_and_user(self, entry_id, user_id):
        return next((e for e in self.entries if e.id == entry_id and e.user_id == user_id and not e.is_deleted), None)

    def get_by_user(self, user_id):
        return [e for e in self.entries if e.user_id == user_id and not e.is_deleted]

    def soft_delete(self, entry):
        entry.is_deleted = True


class FakeJournalTagRepository:
    def __init__(self, tags: list[FakeJournalTag] | None = None):
        self.tags = tags or []
        self.delete_by_entry_calls: list[UUID] = []

    def get_by_entry(self, journal_entry_id):
        return [t for t in self.tags if t.journal_entry_id == journal_entry_id]

    def bulk_create(self, user_id, journal_entry_id, tag_names):
        created = [FakeJournalTag(journal_entry_id=journal_entry_id, tag_name=name, user_id=user_id) for name in tag_names]
        self.tags.extend(created)
        return created

    def delete_by_entry(self, journal_entry_id):
        self.delete_by_entry_calls.append(journal_entry_id)
        before = len(self.tags)
        self.tags = [t for t in self.tags if t.journal_entry_id != journal_entry_id]
        return before - len(self.tags)


@dataclass
class FakeCorporateActionAdjustment:
    user_id: UUID
    instrument_id: UUID
    action_type: str
    ratio: Decimal
    applied_at: datetime
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now())


class FakeCorporateActionRepository:
    def __init__(self, existing: list[FakeCorporateActionAdjustment] | None = None):
        self.existing = existing or []

    def get_duplicate(self, user_id, instrument_id, action_type, applied_at):
        return next(
            (
                a for a in self.existing
                if a.user_id == user_id and a.instrument_id == instrument_id
                and a.action_type == action_type and a.applied_at == applied_at
            ),
            None,
        )

    def create_adjustment(self, user_id, instrument_id, action_type, ratio, applied_at):
        adj = FakeCorporateActionAdjustment(
            user_id=user_id, instrument_id=instrument_id, action_type=action_type,
            ratio=ratio, applied_at=applied_at,
        )
        self.existing.append(adj)
        return adj

    def get_by_user(self, user_id):
        return [a for a in self.existing if a.user_id == user_id]
