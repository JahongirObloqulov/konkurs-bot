import logging
from typing import TYPE_CHECKING

from aiogram import Bot
from aiogram.enums import ChatMemberStatus

if TYPE_CHECKING:
    from app.config import Config

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
        logger.warning(f"Failed to check subscription for user {user_id} in chat {chat_id}: {e}")
        return False


async def check_all_subscriptions(bot: Bot, config: "Config", user_id: int) -> tuple[bool, list[dict]]:
    """Barcha majburiy obunalarni tekshirish.
    Returns: (all_subscribed: bool, unsubscribed_chats: list)"""
    if not config.required_chats:
        return True, []
    
    unsubscribed = []
    for chat in config.required_chats:
        is_subscribed = await check_chat_subscription(bot, chat["id"], user_id)
        if not is_subscribed:
            unsubscribed.append(chat)
    
    return len(unsubscribed) == 0, unsubscribed
