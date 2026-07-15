from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.admin_auth import (
    get_current_admin_user_id,
    get_current_support_or_admin_user_id,
)
from app.db.session import get_db
from app.repositories.admin_audit_log_repository import AdminAuditLogRepository
from app.repositories.auth_user_repository import AuthUserRepository
from app.repositories.broker_connection_repository import BrokerConnectionRepository
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.feature_flag_repository import FeatureFlagRepository
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.trade_repository import TradeRepository
from app.repositories.user_tax_persona_repository import UserTaxPersonaRepository
from app.repositories.vault_repository import VaultRepository
from app.schemas.admin import (
    AdminAuditLogResponse,
    AdminImpersonateView,
    AdminUserDetail,
    AdminUserSummary,
    FeatureFlagResponse,
    SetFeatureFlagRequest,
    SetUserRoleRequest,
)
from app.schemas.csv_import import CsvImportResponse
from app.services.admin_service import AdminService
from app.services.holding_service import HoldingLotService
from app.services.trade_service import TradeService
from app.services.zerodha_service import ZerodhaService

router = APIRouter()


def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    zerodha_service = ZerodhaService(
        broker_connection_repository=BrokerConnectionRepository(db),
        vault_repository=VaultRepository(db),
        trade_service=TradeService(
            trade_repository=TradeRepository(db),
            holding_service=HoldingLotService(
                holding_repository=HoldingLotRepository(db)
            ),
            realized_gain_repository=RealizedGainRepository(db),
        ),
        instrument_repository=InstrumentRepository(db),
    )
    return AdminService(
        auth_user_repository=AuthUserRepository(db),
        user_tax_persona_repository=UserTaxPersonaRepository(db),
        subscription_repository=SubscriptionRepository(db),
        broker_connection_repository=BrokerConnectionRepository(db),
        dashboard_repository=DashboardRepository(db),
        feature_flag_repository=FeatureFlagRepository(db),
        admin_audit_log_repository=AdminAuditLogRepository(db),
        zerodha_service=zerodha_service,
    )


# ── User management (admin only for writes; support+admin for reads) ──────────

@router.get("/admin/users", response_model=list[AdminUserSummary])
def list_users(
    user_id: UUID = Depends(get_current_support_or_admin_user_id),
    service: AdminService = Depends(get_admin_service),
):
    return service.list_users()


@router.get("/admin/users/{target_user_id}", response_model=AdminUserDetail)
def get_user_detail(
    target_user_id: UUID,
    user_id: UUID = Depends(get_current_support_or_admin_user_id),
    service: AdminService = Depends(get_admin_service),
):
    detail = service.get_user_detail(target_user_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"User {target_user_id} not found.")
    return detail


@router.patch("/admin/users/{target_user_id}/role", response_model=AdminUserDetail)
def set_user_role(
    target_user_id: UUID,
    request: SetUserRoleRequest,
    admin_user_id: UUID = Depends(get_current_admin_user_id),
    service: AdminService = Depends(get_admin_service),
):
    try:
        detail = service.set_user_role(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            role=request.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not detail:
        raise HTTPException(status_code=404, detail=f"User {target_user_id} not found.")
    return detail


# ── Feature flags — admin only ─────────────────────────────────────────────────

@router.get("/admin/feature-flags", response_model=list[FeatureFlagResponse])
def list_feature_flags(
    admin_user_id: UUID = Depends(get_current_admin_user_id),
    service: AdminService = Depends(get_admin_service),
):
    return service.list_feature_flags()


@router.post("/admin/feature-flags", response_model=FeatureFlagResponse)
def set_feature_flag(
    request: SetFeatureFlagRequest,
    admin_user_id: UUID = Depends(get_current_admin_user_id),
    service: AdminService = Depends(get_admin_service),
):
    return service.set_feature_flag(
        admin_user_id=admin_user_id,
        flag_key=request.flag_key,
        is_enabled=request.is_enabled,
        description=request.description,
        target_user_id=request.target_user_id,
    )


# ── Impersonation (read-only view + broker resync only) — support+admin ───────

@router.get(
    "/admin/users/{target_user_id}/impersonate-view",
    response_model=AdminImpersonateView,
)
def impersonate_view(
    target_user_id: UUID,
    admin_user_id: UUID = Depends(get_current_support_or_admin_user_id),
    service: AdminService = Depends(get_admin_service),
):
    view = service.impersonate_view(admin_user_id=admin_user_id, target_user_id=target_user_id)
    if not view:
        raise HTTPException(status_code=404, detail=f"User {target_user_id} not found.")
    return view


@router.post(
    "/admin/users/{target_user_id}/impersonate-view/resync-broker/{broker_connection_id}",
    response_model=CsvImportResponse,
)
def impersonate_broker_resync(
    target_user_id: UUID,
    broker_connection_id: UUID,
    admin_user_id: UUID = Depends(get_current_support_or_admin_user_id),
    service: AdminService = Depends(get_admin_service),
):
    try:
        return service.impersonate_broker_resync(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            broker_connection_id=broker_connection_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Audit log — admin only ─────────────────────────────────────────────────────

@router.get("/admin/audit-logs", response_model=list[AdminAuditLogResponse])
def list_audit_logs(
    admin_user_id: UUID = Depends(get_current_admin_user_id),
    service: AdminService = Depends(get_admin_service),
):
    return service.list_audit_logs()
