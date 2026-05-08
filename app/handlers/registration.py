from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.config import Config
from app.db.models import User
from app.keyboards.inline import get_main_menu_kb, get_subscription_kb
from app.services.subscription_service import check_all_subscriptions
from app.services.settings_service import get_setting

router = Router()

class RegistrationState(StatesGroup):
    first_name = State()
    last_name = State()
    phone = State()
    location = State()
    check_sub = State()

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
        success_text = await get_setting(session, "registration_success", "✅ Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!")
        await state.clear()
        await message.answer(success_text, reply_markup=get_main_menu_kb())

@router.callback_query(RegistrationState.check_sub, F.data == "check_sub")
async def process_check_sub(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    is_subscribed, unsubscribed_chats = await check_all_subscriptions(bot, callback.from_user.id, session)
    
    if not is_subscribed:
        await callback.answer("❌ Hali hamma kanallarga obuna bo'lmadingiz!", show_alert=True)
        # Update keyboard if some channels were joined
        await callback.message.edit_reply_markup(reply_markup=get_subscription_kb(unsubscribed_chats))
    else:
        success_text = await get_setting(session, "subscription_success", "✅ Tabriklaymiz! Obuna tasdiqlandi. Endi botdan to'liq foydalanishingiz mumkin.")
        await state.clear()
        await callback.message.answer(success_text, reply_markup=get_main_menu_kb())
        await callback.message.delete()
