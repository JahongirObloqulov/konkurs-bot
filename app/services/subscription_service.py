# v1.0.1 - Fixed imports
import logging
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.settings_service import get_required_chats

logger = logging.getLogger(__name__)


async def check_chat_subscription(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Foydalanuvchining kanal/guruhga obuna bo'lganligini tekshirish."""
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        )
    except Exception as e:
        # Ignore errors if bot is not admin or chat not found
        return False


async def check_all_subscriptions(bot: Bot, user_id: int, session: AsyncSession) -> tuple[bool, list[dict]]:
    """Barcha majburiy obunalarni tekshirish.
    Returns: (all_subscribed: bool, unsubscribed_chats: list)"""
    required_chats = await get_required_chats(session)
    
    if not required_chats:
        return True, []
    
    unsubscribed = []
    for chat in required_chats:
        is_subscribed = await check_chat_subscription(bot, chat["id"], user_id)
        if not is_subscribed:
            unsubscribed.append(chat)
    
    return len(unsubscribed) == 0, unsubscribed
