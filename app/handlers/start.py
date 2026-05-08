from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Config
from app.keyboards.inline import get_admin_menu_kb, get_main_menu_kb
from app.services.user_service import get_or_create_user

from aiogram.fsm.context import FSMContext

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, config: Config, state: FSMContext):
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

    # 1. Check subscriptions first
    if config.required_chats:
        from app.services.subscription_service import check_all_subscriptions
        from app.keyboards.inline import get_subscription_kb
        
        all_subscribed, unsubscribed = await check_all_subscriptions(message.bot, config, user.id)
        if not all_subscribed:
            await message.answer(
                "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling!</b>\n\n"
                "Barcha kanallarga obuna bo'lgach, \"Obunani tekshirish\" tugmasini bosing.",
                reply_markup=get_subscription_kb(unsubscribed, 0), # 0 means start check
                parse_mode="HTML"
            )
            return

    # 2. Check if registered
    if not user_obj.is_registered:
        from app.handlers.registration import start_registration
        await start_registration(message, state)
        return

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
