from aiogram import Bot
from aiogram.enums import ChatMemberStatus


async def check_subscription(bot: Bot, channel_id: int, user_id: int) -> bool:
    """Foydalanuvchining kanalga obuna bo'lganligini tekshirish."""
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        )
    except Exception:
        return False
