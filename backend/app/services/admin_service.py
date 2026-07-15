from uuid import UUID

from app.repositories.admin_audit_log_repository import AdminAuditLogRepository
from app.repositories.auth_user_repository import AuthUserRepository
from app.repositories.broker_connection_repository import BrokerConnectionRepository
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.feature_flag_repository import FeatureFlagRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_tax_persona_repository import UserTaxPersonaRepository
from app.services.zerodha_service import ZerodhaService

VALID_ROLES = {"user", "support", "admin"}


class AdminService:
    """
    Phase 14 — Admin Panel. Every mutating action here writes an
    admin_audit_logs row (BRD FR-ADM-02's "full audit"), whether the
    action is a role change, a feature-flag edit, or an impersonation
    view/resync.

    Impersonation scope note: BRD FR-ADM-02 specifies "read-only +
    broker re-sync only". This is implemented as data-viewing endpoints
    that query the target user's own data on the ADMIN's behalf — never
    a real session swap (no Supabase service-role key exists in this
    project to mint a session as another user, and doing so would be a
    materially bigger, more security-sensitive feature than what was
    asked for). An admin never "becomes" the user in this app; they see
    a read-only summary and can trigger the one write BRD explicitly
    permits (broker resync), always attributed to the admin's own
    action in the audit log, never disguised as the target user acting.
    "User notified" (also in FR-ADM-02) is NOT implemented — no
    notification system (FR-NOT-*) exists yet in this project.
    """

    def __init__(
        self,
        auth_user_repository: AuthUserRepository,
        user_tax_persona_repository: UserTaxPersonaRepository,
        subscription_repository: SubscriptionRepository,
        broker_connection_repository: BrokerConnectionRepository,
        dashboard_repository: DashboardRepository,
        feature_flag_repository: FeatureFlagRepository,
        admin_audit_log_repository: AdminAuditLogRepository,
        zerodha_service: ZerodhaService,
    ):
        self.auth_user_repository = auth_user_repository
        self.user_tax_persona_repository = user_tax_persona_repository
        self.subscription_repository = subscription_repository
        self.broker_connection_repository = broker_connection_repository
        self.dashboard_repository = dashboard_repository
        self.feature_flag_repository = feature_flag_repository
        self.admin_audit_log_repository = admin_audit_log_repository
        self.zerodha_service = zerodha_service

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    def list_users(self) -> list[dict]:
        auth_rows = self.auth_user_repository.get_all()
        personas = {
            p.user_id: p for p in self.user_tax_persona_repository.get_all()
        }
        subscriptions = {
            s.user_id: s for s in self.subscription_repository.get_all()
        }

        users = []
        for row in auth_rows:
            persona = personas.get(row.id)
            subscription = subscriptions.get(row.id)
            users.append({
                "user_id": row.id,
                "email": row.email,
                "created_at": row.created_at,
                "role": persona.role if persona else "user",
                "plan_id": subscription.plan_id if subscription else "free",
                "subscription_status": subscription.status if subscription else "active",
            })
        return users

    def get_user_detail(self, user_id: UUID) -> dict | None:
        auth_row = self.auth_user_repository.get_by_id(user_id)
        if not auth_row:
            return None
        persona = self.user_tax_persona_repository.get_by_user(user_id)
        subscription = self.subscription_repository.get_by_user(user_id)
        broker_connections = self.broker_connection_repository.get_by_user(user_id)
        return {
            "user_id": auth_row.id,
            "email": auth_row.email,
            "created_at": auth_row.created_at,
            "role": persona.role if persona else "user",
            "plan_id": subscription.plan_id if subscription else "free",
            "subscription_status": subscription.status if subscription else "active",
            "broker_connections": [
                {"id": bc.id, "broker_name": bc.broker_name, "status": bc.status}
                for bc in broker_connections
            ],
        }

    def set_user_role(
        self, admin_user_id: UUID, target_user_id: UUID, role: str
    ) -> dict | None:
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {sorted(VALID_ROLES)}")

        auth_row = self.auth_user_repository.get_by_id(target_user_id)
        if not auth_row:
            return None

        persona = self.user_tax_persona_repository.get_or_create(target_user_id)
        previous_role = persona.role
        self.user_tax_persona_repository.update_role(persona, role)

        self.admin_audit_log_repository.log(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            action="role_change",
            context={"previous_role": previous_role, "new_role": role},
        )

        return self.get_user_detail(target_user_id)

    # ------------------------------------------------------------------
    # Feature flags — BRD FR-ADM-01
    # ------------------------------------------------------------------

    def list_feature_flags(self) -> list:
        return self.feature_flag_repository.get_all()

    def set_feature_flag(
        self,
        admin_user_id: UUID,
        flag_key: str,
        is_enabled: bool,
        description: str | None = None,
        target_user_id: UUID | None = None,
    ):
        flag = self.feature_flag_repository.upsert(
            flag_key=flag_key,
            is_enabled=is_enabled,
            description=description,
            user_id=target_user_id,
        )
        self.admin_audit_log_repository.log(
            admin_user_id=admin_user_id,
            # A global flag (no target user) is still attributed to the
            # admin for audit purposes — admin_audit_logs.target_user_id
            # is NOT NULL, so a global change is logged against the
            # acting admin themselves.
            target_user_id=target_user_id or admin_user_id,
            action="feature_flag_set",
            context={
                "flag_key": flag_key,
                "is_enabled": is_enabled,
                "scope": "user" if target_user_id else "global",
            },
        )
        return flag

    def check_feature_flag(self, flag_key: str, user_id: UUID) -> bool:
        """For other parts of the app to call later — per-user override
        takes precedence over the global default; no rows at all is False."""
        override = self.feature_flag_repository.get_user_override(flag_key, user_id)
        if override:
            return override.is_enabled
        global_flag = self.feature_flag_repository.get_global(flag_key)
        return global_flag.is_enabled if global_flag else False

    # ------------------------------------------------------------------
    # Impersonation — read-only view + broker resync only (BRD FR-ADM-02)
    # ------------------------------------------------------------------

    def impersonate_view(self, admin_user_id: UUID, target_user_id: UUID) -> dict | None:
        detail = self.get_user_detail(target_user_id)
        if not detail:
            return None

        dashboard = self.dashboard_repository.get_by_user(target_user_id)
        detail["dashboard_summary"] = (
            {
                "total_equity_value": dashboard.total_equity_value,
                "total_crypto_value": dashboard.total_crypto_value,
                "day_pnl": dashboard.day_pnl,
                "unrealized_pnl": dashboard.unrealized_pnl,
            }
            if dashboard
            else None
        )

        self.admin_audit_log_repository.log(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            action="impersonation_view",
        )
        return detail

    def impersonate_broker_resync(
        self,
        admin_user_id: UUID,
        target_user_id: UUID,
        broker_connection_id: UUID,
    ):
        result = self.zerodha_service.sync_today_trades(
            user_id=target_user_id,
            broker_connection_id=broker_connection_id,
        )
        self.admin_audit_log_repository.log(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            action="impersonation_broker_resync",
            context={
                "broker_connection_id": str(broker_connection_id),
                "imported": result.imported,
                "skipped": result.skipped,
            },
        )
        return result

    def list_audit_logs(self, limit: int = 100) -> list:
        return self.admin_audit_log_repository.get_recent(limit=limit)
