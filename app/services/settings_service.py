import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Settings

logger = logging.getLogger(__name__)


async def get_setting(session: AsyncSession, key: str, default: Any = None) -> Any:
    """Sozlamani olish."""
    try:
        result = await session.execute(select(Settings).where(Settings.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            return json.loads(setting.value)
        return default
    except Exception as e:
        logger.error(f"Failed to get setting {key}: {e}")
        return default


async def set_setting(session: AsyncSession, key: str, value: Any) -> bool:
    """Sozlamani saqlash."""
    try:
        result = await session.execute(select(Settings).where(Settings.key == key))
        setting = result.scalar_one_or_none()
        
        value_str = json.dumps(value)
        
        if setting:
            setting.value = value_str
        else:
            setting = Settings(key=key, value=value_str)
            session.add(setting)
        
        await session.commit()
        logger.info(f"Setting updated: {key}")
        return True
    except Exception as e:
        logger.error(f"Failed to set setting {key}: {e}")
        await session.rollback()
        return False


async def get_required_chats(session: AsyncSession) -> list[dict]:
    """Majburiy obuna kanallarini olish."""
    return await get_setting(session, "required_chats", default=[])


async def set_required_chats(session: AsyncSession, chats: list[dict]) -> bool:
    """Majburiy obuna kanallarini saqlash."""
    return await set_setting(session, "required_chats", chats)
