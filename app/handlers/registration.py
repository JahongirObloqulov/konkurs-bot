from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
import logging

from app.config import Config
from app.db.models import User
from app.keyboards.inline import get_subscription_kb
from app.keyboards.reply import get_main_reply_kb
from app.services.subscription_service import check_all_subscriptions
from app.services.settings_service import get_setting

logger = logging.getLogger(__name__)
router = Router()

class RegistrationState(StatesGroup):
    first_name = State()
    last_name = State()
    phone = State()
    location = State()
    check_sub = State()

async def send_sub_success_message(target: Message | CallbackQuery, session: AsyncSession, bot: Bot):
    """Obuna muvaffaqiyatli xabarini (ixtiyoriy media bilan) yuborish."""
    success_text = await get_setting(session, "subscription_success", "✅ Tabriklaymiz! Obuna tasdiqlandi. Endi botdan to'liq foydalanishingiz mumkin.")
    media_id = await get_setting(session, "sub_success_media_id")
    media_type = await get_setting(session, "sub_success_media_type")
    
    kb = get_main_reply_kb()
    
    # Message object to send to
    msg = target if isinstance(target, Message) else target.message

    if media_id and media_type:
        try:
            if media_type == "photo":
                await bot.send_photo(msg.chat.id, photo=media_id, caption=success_text, reply_markup=kb, parse_mode="HTML")
            elif media_type == "video":
                await bot.send_video(msg.chat.id, video=media_id, caption=success_text, reply_markup=kb, parse_mode="HTML")
            elif media_type == "video_note":
                await bot.send_video_note(msg.chat.id, video_note=media_id)
                await bot.send_message(msg.chat.id, success_text, reply_markup=kb, parse_mode="HTML")
            elif media_type == "audio":
                await bot.send_audio(msg.chat.id, audio=media_id, caption=success_text, reply_markup=kb, parse_mode="HTML")
            elif media_type == "document":
                await bot.send_document(msg.chat.id, document=media_id, caption=success_text, reply_markup=kb, parse_mode="HTML")
            return
        except Exception as e:
            logger.error(f"Failed to send success media: {e}")
            # Fallback to plain text if media fails
    
    await bot.send_message(msg.chat.id, success_text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "start_registration")
async def start_registration_cb(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    welcome_text = await get_setting(session, "registration_welcome", "Xush kelibsiz! Ro'yxatdan o'tishni boshlaymiz.\n\nIsmingizni kiriting:")
    await state.set_state(RegistrationState.first_name)
    await callback.message.answer(welcome_text, reply_markup=ReplyKeyboardRemove())
    await callback.message.delete()

async def start_registration(message: Message, state: FSMContext, session: AsyncSession):
    welcome_text = await get_setting(session, "registration_welcome", "Xush kelibsiz! Ro'yxatdan o'tishni boshlaymiz.\n\nIsmingizni kiriting:")
    await state.set_state(RegistrationState.first_name)
    await message.answer(welcome_text, reply_markup=ReplyKeyboardRemove())

@router.message(RegistrationState.first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text.strip())
    await state.set_state(RegistrationState.last_name)
    await message.answer("Familiyangizni kiriting:")

@router.message(RegistrationState.last_name)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text.strip())
    await state.set_state(RegistrationState.phone)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Telefon raqamingizni yuboring (tugmani bosing):", reply_markup=kb)

@router.message(RegistrationState.phone, F.contact | F.text)
async def process_phone(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip()
    
    await state.update_data(phone=phone)
    await state.set_state(RegistrationState.location)
    await message.answer("Yashash joyingizni kiriting (Viloyat, tuman):", reply_markup=ReplyKeyboardRemove())

@router.message(RegistrationState.location)
async def process_location(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    location = message.text.strip()
    
    # Update user in DB
    await session.execute(
        update(User)
        .where(User.user_id == message.from_user.id)
        .values(
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone=data["phone"],
            location=location,
            is_registered=True
        )
    )
    await session.commit()
    
    try:
        from web.routes import notify_sse
        await notify_sse("user_registered")
    except Exception as e:
        logger.error(f"Failed to notify SSE: {e}")
    
    # Check mandatory subscription after registration
    is_subscribed, unsubscribed_chats = await check_all_subscriptions(bot, message.from_user.id, session)
    
    if not is_subscribed:
        sub_required_text = await get_setting(session, "subscription_required", "✅ Ro'yxatdan o'tdingiz!\n\nLekin botdan foydalanish uchun quyidagi kanallarga obuna bo'lishingiz shart:")
        await state.set_state(RegistrationState.check_sub)
        await message.answer(
            sub_required_text,
            reply_markup=get_subscription_kb(unsubscribed_chats)
        )
    else:
        await state.clear()
        await send_sub_success_message(message, session, bot)

@router.callback_query(RegistrationState.check_sub, F.data == "check_sub")
async def process_check_sub(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    is_subscribed, unsubscribed_chats = await check_all_subscriptions(bot, callback.from_user.id, session)
    
    if not is_subscribed:
        await callback.answer("❌ Hali hamma kanallarga obuna bo'lmadingiz!", show_alert=True)
        # Update keyboard if some channels were joined
        await callback.message.edit_reply_markup(reply_markup=get_subscription_kb(unsubscribed_chats))
    else:
        await state.clear()
        await send_sub_success_message(callback, session, bot)
        await callback.message.delete()
