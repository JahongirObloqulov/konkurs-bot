import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Settings

logger = logging.getLogger(__name__)


async def get_setting(session: AsyncSession, key: str, default: Any = None, bot_id: Optional[int] = None) -> Any:
    """Sozlamani olish. Bot-specific bo'lsa uni oladi, bo'lmasa globalni."""
    try:
        if bot_id:
            # Try bot-specific first
            result = await session.execute(
                select(Settings).where(Settings.key == key, Settings.bot_id == bot_id)
            )
            setting = result.scalar_one_or_none()
            if setting:
                return json.loads(setting.value)
        
        # Fallback to global
        result = await session.execute(
            select(Settings).where(Settings.key == key, Settings.bot_id == None)
        )
        setting = result.scalar_one_or_none()
        if setting:
            return json.loads(setting.value)
            
        return default
    except Exception as e:
        logger.error(f"Failed to get setting {key} for bot {bot_id}: {e}")
        return default


async def set_setting(session: AsyncSession, key: str, value: Any, bot_id: Optional[int] = None) -> bool:
    """Sozlamani saqlash (bot-specific yoki global)."""
    try:
        result = await session.execute(
            select(Settings).where(Settings.key == key, Settings.bot_id == bot_id)
        )
        setting = result.scalar_one_or_none()
        
        value_str = json.dumps(value)
        
        if setting:
            setting.value = value_str
            setting.updated_at = datetime.now(timezone.utc)
        else:
            setting = Settings(key=key, value=value_str, bot_id=bot_id)
            session.add(setting)
        
        await session.commit()
        logger.info(f"Setting updated: {key} (Bot: {bot_id})")
        return True
    except Exception as e:
        logger.error(f"Failed to set setting {key} for bot {bot_id}: {e}")
        await session.rollback()
        return False


from app.db.models import Settings, RequiredChat

async def get_required_chats(session: AsyncSession, bot_id: Optional[int] = None) -> list[dict]:
    """Majburiy obuna kanallarini olish."""
    query = select(RequiredChat)
    if bot_id:
        # Get bot-specific chats OR global chats (bot_id is null)
        from sqlalchemy import or_
        query = query.where(or_(RequiredChat.bot_id == bot_id, RequiredChat.bot_id == None))
    
    result = await session.execute(query)
    chats = result.scalars().all()
    
    return [
        {
            "id": c.id,
            "chat_id": c.chat_id,
            "title": c.title,
            "url": c.url,
            "bot_id": c.bot_id
        }
        for c in chats
    ]


async def add_required_chat(
    session: AsyncSession, 
    chat_id: int, 
    title: str, 
    url: str, 
    bot_id: Optional[int] = None
) -> RequiredChat:
    """Yangi majburiy kanal qo'shish."""
    chat = RequiredChat(chat_id=chat_id, title=title, url=url, bot_id=bot_id)
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return chat


async def delete_required_chat(session: AsyncSession, chat_internal_id: int) -> bool:
    """Majburiy kanalni o'chirish."""
    chat = await session.get(RequiredChat, chat_internal_id)
    if chat:
        await session.delete(chat)
        await session.commit()
        return True
    return False


async def set_required_chats(session: AsyncSession, chats: list[dict]) -> bool:
    """
    Eski formatni qo'llab-quvvatlash uchun (migration).
    Bu funksiya endi barcha eski kanallarni o'chirib, yangilarini qo'shadi.
    """
    try:
        from sqlalchemy import delete
        await session.execute(delete(RequiredChat))
        
        for c in chats:
            chat = RequiredChat(
                chat_id=c.get('chat_id'),
                title=c.get('title'),
                url=c.get('url'),
                bot_id=c.get('bot_id')
            )
            session.add(chat)
        
        await session.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to migrate required chats: {e}")
        await session.rollback()
        return False
