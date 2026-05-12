from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, LabeledPrice
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.shop_service import get_active_products, get_product_by_id, create_order
from app.utils.translations import translate

router = Router()

@router.message(Command("courses"))
@router.message(F.text == "🎓 Kurslar")
async def show_courses(message: Message, session: AsyncSession):
    products = await get_active_products(session)
    
    if not products:
        await message.answer("Hozircha sotuvda kurslar yo'q.")
        return

    text = "<b>🎓 Bizning online kurslar va treninglarimiz</b>\n\nQuyidagilardan birini tanlang:"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for p in products:
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{p.name} — {p.price} so'm", callback_query_data=f"prod_{p.id}")])
    
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("prod_"))
async def show_product_detail(callback: CallbackQuery, session: AsyncSession):
    product_id = int(callback.data.split("_")[1])
    product = await get_product_by_id(session, product_id)
    
    if not product:
        await callback.answer("Kurs topilmadi.")
        return

    text = (
        f"<b>📘 {product.name}</b>\n\n"
        f"{product.description}\n\n"
        f"💰 Narxi: <b>{product.price} so'm</b>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Sotib olish", callback_query_data=f"buy_{product.id}")],
        [InlineKeyboardButton(text="⬅️ Kurslarga qaytish", callback_query_data="back_to_courses")]
    ])
    
    if product.media_id:
        if product.media_type == "photo":
            await callback.message.answer_photo(product.media_id, caption=text, reply_markup=kb, parse_mode="HTML")
        elif product.media_type == "video":
            await callback.message.answer_video(product.media_id, caption=text, reply_markup=kb, parse_mode="HTML")
        await callback.message.delete()
    else:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    product_id = int(callback.data.split("_")[1])
    product = await get_product_by_id(session, product_id)
    
    if not product:
        await callback.answer("Kurs topilmadi.")
        return

    # Create order
    order = await create_order(session, callback.from_user.id, product.id, product.price)
    
    # In a real scenario, here we send an invoice
    # For now, we just simulate the payment process or send payment details
    text = (
        f"<b>🛒 Buyurtma #{order.id}</b>\n\n"
        f"Kurs: {product.name}\n"
        f"To'lov miqdori: {product.price} so'm\n\n"
        "To'lov qilish uchun Click/Payme havolasi yoki karta ma'lumotlarini shu yerda ko'rsatish mumkin.\n\n"
        "<i>To'lov tasdiqlangandan so'ng kursga kirish huquqi beriladi.</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ To'ladim (Simulyatsiya)", callback_query_data=f"pay_confirm_{order.id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_query_data="back_to_courses")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "back_to_courses")
async def back_to_courses(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    await show_courses(callback.message, session)
