from aiogram import Bot, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Config
from app.keyboards.inline import get_admin_menu_kb, get_contest_detail_kb, get_main_menu_kb
from app.services.contest_service import (
    add_participant,
    get_contest_by_id,
    get_participants_count,
    is_participant,
)
from app.services.subscription_service import check_subscription
from app.services.user_service import get_or_create_user
from app.utils.formatting import format_contest_view

router = Router()


@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(
    message: Message, session: AsyncSession, config: Config, bot: Bot
):
    user = message.from_user
    if not user:
        return

    await get_or_create_user(
        session,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await _send_main_menu(message, user, config)
        return

    payload = args[1]

    if payload.startswith("ref_"):
        parts = payload.split("_")
        if len(parts) >= 3:
            try:
                contest_id = int(parts[1])
                referrer_id = int(parts[2])
            except ValueError:
                await _send_main_menu(message, user, config)
                return

            if referrer_id == user.id:
                await _send_main_menu(message, user, config)
                return

            contest = await get_contest_by_id(session, contest_id)
            if not contest or not contest.is_active:
                await message.answer(
                    "\u274c Konkurs topilmadi yoki tugagan!",
                    reply_markup=get_main_menu_kb(),
                )
                return

            if contest.require_subscription and config.channel_id:
                is_subscribed = await check_subscription(bot, config.channel_id, user.id)
                if not is_subscribed:
                    from app.keyboards.inline import get_subscription_kb
                    await message.answer(
                        "\u26a0\ufe0f <b>Ishtirok etish uchun kanalimizga obuna bo'ling!</b>",
                        reply_markup=get_subscription_kb(config.channel_username, contest_id),
                        parse_mode="HTML",
                    )
                    return

            already = await is_participant(session, contest_id, user.id)
            if already:
                participants_count = await get_participants_count(session, contest_id)
                text = format_contest_view(contest, participants_count)
                await message.answer(
                    text + "\n\u2705 Siz allaqachon ishtirok etyapsiz!",
                    reply_markup=get_contest_detail_kb(contest, True),
                    parse_mode="HTML",
                )
                return

            participant = await add_participant(
                session,
                contest_id=contest_id,
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
                referred_by=referrer_id,
            )

            participants_count = await get_participants_count(session, contest_id)
            text = format_contest_view(contest, participants_count)

            if participant:
                text += "\n\u2705 Siz muvaffaqiyatli ro'yxatdan o'tdingiz!"
            else:
                text += "\n\u2705 Siz allaqachon ishtirok etyapsiz!"

            await message.answer(
                text,
                reply_markup=get_contest_detail_kb(contest, True),
                parse_mode="HTML",
            )
            return

    await _send_main_menu(message, user, config)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, config: Config):
    user = message.from_user
    if not user:
        return

    await get_or_create_user(
        session,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )

    await _send_main_menu(message, user, config)


async def _send_main_menu(message: Message, user, config: Config):
    text = (
        f"Assalomu alaykum, {user.full_name}! \U0001f44b\n\n"
        "\U0001f3c6 <b>Konkurs Bot</b>ga xush kelibsiz!\n\n"
        "Bu bot orqali siz turli konkurslarda ishtirok etishingiz "
        "va sovg'alar yutib olishingiz mumkin.\n\n"
        "Quyidagi tugmalardan birini tanlang:"
    )

    if config.is_admin(user.id):
        text += "\n\n\U0001f6e0 <i>Siz admin sifatida kirgansiz</i>"
        kb = get_admin_menu_kb()
    else:
        kb = get_main_menu_kb()

    await message.answer(text, reply_markup=kb, parse_mode="HTML")
