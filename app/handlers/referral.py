from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.referral_service import get_top_referrers, get_user_referral_stats
from app.utils.translations import translate

router = Router()

@router.message(Command("referral"))
@router.message(F.text == "👥 Referallar")
async def cmd_referral(message: Message, session: AsyncSession, bot: Bot):
    user_id = message.from_user.id
    lang = "uz" # Default to uz for now, or get from user_obj
    
    # Get user stats
    stats = await get_user_referral_stats(session, user_id)
    if not stats:
        await message.answer("Xatolik yuz berdi.")
        return

    bot_user = await bot.get_me()
    referral_link = f"https://t.me/{bot_user.username}?start=ref{user_id}"
    
    text = (
        "<b>👥 Referal tizimi</b>\n\n"
        f"Sizning referal havolangiz:\n<code>{referral_link}</code>\n\n"
        f"📊 Siz taklif qilganlar: <b>{stats['referral_count']} ta</b>\n"
        f"🏆 Sizning o'rningiz: <b>{stats['rank']}-o'rin</b>\n\n"
        "Do'stlaringizni taklif qiling va sovg'alarga ega bo'ling!"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Reyting (Top 10)", callback_query_data="top_referrers")],
        [InlineKeyboardButton(text="🔗 Havolani ulashish", url=f"https://t.me/share/url?url={referral_link}&text=Konkursda qatnashing va yutib oling!")]
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "top_referrers")
async def show_top_referrers(callback: CallbackQuery, session: AsyncSession):
    top_users = await get_top_referrers(session, limit=10)
    
    text = "<b>🏆 Eng faol foydalanuvchilar (Top 10)</b>\n\n"
    
    if not top_users:
        text += "Hozircha faollar yo'q."
    else:
        for i, user in enumerate(top_users, 1):
            name = user.full_name or "Foydalanuvchi"
            text += f"{i}. {name} — <b>{user.referral_count} ta</b>\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_query_data="back_to_referral")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "back_to_referral")
async def back_to_referral(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    await callback.message.delete()
    # Re-call the referral command logic
    # Simplified: just send a new message
    await cmd_referral(callback.message, session, bot)
