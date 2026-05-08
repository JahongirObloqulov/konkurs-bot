from datetime import datetime, timezone
from app.db.models import AuditLog
from sqlalchemy.ext.asyncio import AsyncSession

async def log_action(session: AsyncSession, admin_username: str, action: str, details: str = None):
    """
    Logs an admin action to the audit_logs table.
    """
    log = AuditLog(
        admin_username=admin_username,
        action=action,
        details=details,
        created_at=datetime.now(timezone.utc)
    )
    session.add(log)
    await session.commit()
