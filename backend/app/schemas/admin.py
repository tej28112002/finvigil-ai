from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AdminUserSummary(BaseModel):
    user_id: UUID
    email: str | None
    created_at: datetime | None
    role: str
    plan_id: str
    subscription_status: str


class BrokerConnectionSummary(BaseModel):
    id: UUID
    broker_name: str
    status: str


class AdminUserDetail(BaseModel):
    user_id: UUID
    email: str | None
    created_at: datetime | None
    role: str
    plan_id: str
    subscription_status: str
    broker_connections: list[BrokerConnectionSummary]


class DashboardSummary(BaseModel):
    total_equity_value: Decimal
    total_crypto_value: Decimal
    day_pnl: Decimal
    unrealized_pnl: Decimal


class AdminImpersonateView(AdminUserDetail):
    dashboard_summary: DashboardSummary | None


class SetUserRoleRequest(BaseModel):
    role: str


class FeatureFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flag_key: str
    user_id: UUID | None
    is_enabled: bool
    description: str | None


class SetFeatureFlagRequest(BaseModel):
    flag_key: str
    is_enabled: bool
    description: str | None = None
    target_user_id: UUID | None = None


class AdminAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    admin_user_id: UUID
    target_user_id: UUID
    action: str
    context: dict[str, Any] | None
    created_at: datetime
