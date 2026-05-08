from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import increment_addition_count

router = Router()


@router.message(F.new_chat_members)
async def on_user_added(message: Message, session: AsyncSession):
    inviter = message.from_user
    if not inviter:
        return

    # Check if the inviter is one of the new members (joining via link)
    # or if the inviter added others
    for member in message.new_chat_members:
        if inviter.id != member.id:
            await increment_addition_count(session, inviter.id)
