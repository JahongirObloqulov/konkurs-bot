from aiogram import Router, Bot, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext

from app.config import Config
from app.keyboards.inline import get_subscription_kb, get_language_kb
from app.keyboards.reply import get_admin_reply_kb, get_main_reply_kb
from app.services.user_service import get_or_create_user, update_user_language
from app.services.subscription_service import check_all_subscriptions
from app.services.settings_service import get_setting
from app.handlers.registration import start_registration

from app.utils.translations import translate

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

    lang = user_obj.language_code or "uz"
    
    # NEW: Check if language is set (first time)
    data = await state.get_data()
    if not user_obj.is_registered and "lang_selected" not in data:
        await message.answer(
            translate('choose_language', lang),
            reply_markup=get_language_kb()
        )
        return

    # 1. Check if registered
    if not user_obj.is_registered:
        await start_registration(message, state, session)
        return

    # 2. Check subscriptions
    is_subscribed, unsubscribed_chats = await check_all_subscriptions(bot, user.id, session)
    if not is_subscribed:
        sub_required_text = await get_setting(session, f"subscription_required_{lang}", translate('sub_required_title', lang))
        await message.answer(
            sub_required_text,
            reply_markup=get_subscription_kb(unsubscribed_chats, 0),
            parse_mode="HTML"
        )
        return

    # 3. Main Menu
    text = translate('start_welcome', lang).format(name=user.full_name)

    if config.is_admin(user.id) or user_obj.is_admin:
        text += translate('admin_panel_hint', lang)
        kb = get_admin_reply_kb()
    else:
        kb = get_main_reply_kb()

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("set_lang_"))
async def process_set_lang(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot, config: Config):
    lang_code = callback.data.split("_")[2]
    await update_user_language(session, callback.from_user.id, lang_code)
    await state.update_data(lang_selected=True)
    
    welcome_texts = {
        "uz": "✅ Til tanlandi: O'zbekcha",
        "ru": "✅ Язык выбран: Русский",
        "en": "✅ Language selected: English"
    }
    await callback.answer(welcome_texts.get(lang_code, "✅"))
    
    # After selecting language, proceed to registration or main menu
    user_obj = await get_or_create_user(session, callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    
    if not user_obj.is_registered:
        await start_registration(callback.message, state, session)
    else:
        # Show main menu
        text = (
            f"Assalomu alaykum, {callback.from_user.full_name}! \U0001f44b\n\n"
            "\U0001f3c6 <b>Konkurs Bot</b>ga xush kelibsiz!"
        )
        if config.is_admin(callback.from_user.id) or user_obj.is_admin:
            kb = get_admin_reply_kb()
        else:
            kb = get_main_reply_kb()
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    
    await callback.message.delete()
