from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext

from app.config import Config
from app.keyboards.inline import get_admin_menu_kb, get_main_menu_kb, get_subscription_kb
from app.services.user_service import get_or_create_user
from app.services.subscription_service import check_all_subscriptions
from app.services.settings_service import get_setting
from app.handlers.registration import start_registration

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, config: Config, state: FSMContext, bot: Bot):
    user = message.from_user
    if not user:
        return

    # Handle referral
    referred_by_id = None
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref"):
        try:
            referred_by_id = int(args[1].replace("ref", ""))
        except ValueError:
            pass

    user_obj = await get_or_create_user(
        session,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        referred_by_id=referred_by_id,
    )
    if not user_obj:
        await message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
        return

    # 1. Check if registered
    if not user_obj.is_registered:
        await start_registration(message, state, session)
        return

    # 2. Check subscriptions
    is_subscribed, unsubscribed_chats = await check_all_subscriptions(bot, user.id, session)
    if not is_subscribed:
        sub_required_text = await get_setting(session, "subscription_required", "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling!</b>\n\nBarcha kanallarga obuna bo'lgach, \"Obunani tekshirish\" tugmasini bosing.")
        await message.answer(
            sub_required_text,
            reply_markup=get_subscription_kb(unsubscribed_chats),
            parse_mode="HTML"
        )
        return

    # 3. Main Menu
    text = (
        f"Assalomu alaykum, {user.full_name}! \U0001f44b\n\n"
        "\U0001f3c6 <b>Konkurs Bot</b>ga xush kelibsiz!\n\n"
        "Bu bot orqali siz turli konkurslarda ishtirok etishingiz "
        "va sovg'alar yutib olishingiz mumkin.\n\n"
        "Quyidagi tugmalardan birini tanlang:"
    )

    if config.is_admin(user.id) or user_obj.is_admin:
        text += "\n\n\U0001f6e0 <i>Siz admin sifatida kirgansiz</i>"
        kb = get_admin_menu_kb()
    else:
        kb = get_main_menu_kb()

    await message.answer(text, reply_markup=kb, parse_mode="HTML")
