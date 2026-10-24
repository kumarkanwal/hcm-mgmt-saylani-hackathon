import re
from collections.abc import Mapping
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.audit import AuditLog

SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "old_password",
    "new_password",
    "token",
    "access_token",
    "jwt_secret",
    "api_key",
    "ai_api_key",
    "authorization",
}


def sanitize_audit_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: sanitize_audit_value(item)
            for key, item in value.items()
            if re.sub(r"[^a-z0-9]", "", str(key).lower())
            not in {re.sub(r"[^a-z0-9]", "", key) for key in SENSITIVE_KEYS}
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_audit_value(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def write_audit_log(
    session: Session,
    *,
    actor_id: int | None,
    action: str,
    entity: str,
    entity_id: int,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        before=(
            sanitize_audit_value(
                jsonable_encoder(before, custom_encoder={Decimal: str})
            )
            if before is not None
            else None
        ),
        after=sanitize_audit_value(
            jsonable_encoder(after, custom_encoder={Decimal: str})
        )
        if after is not None
        else None,
    )
    session.add(entry)
    return entry


def list_audit_logs(
    session: Session,
    *,
    entity: str | None,
    actor_id: int | None,
    from_date: date | None,
    to_date: date | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    conditions = []
    if entity:
        conditions.append(AuditLog.entity == entity)
    if actor_id is not None:
        conditions.append(AuditLog.actor_id == actor_id)
    company_timezone = ZoneInfo(get_settings().company_timezone)
    if from_date is not None:
        conditions.append(
            AuditLog.created_at
            >= datetime.combine(
                from_date, time.min, tzinfo=company_timezone
            ).astimezone(UTC)
        )
    if to_date is not None:
        conditions.append(
            AuditLog.created_at
            < datetime.combine(
                to_date + timedelta(days=1), time.min, tzinfo=company_timezone
            ).astimezone(UTC)
        )

    total = session.scalar(select(func.count(AuditLog.id)).where(*conditions)) or 0
    items = session.scalars(
        select(AuditLog)
        .where(*conditions)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}
