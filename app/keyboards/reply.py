from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_admin_reply_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="➕ Konkurs yaratish"))
    builder.row(KeyboardButton(text="📋 Barcha konkurslar"))
    builder.row(KeyboardButton(text="📢 Kanal/Guruh boshqaruvi"))
    builder.row(KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📢 Xabar tarqatish"))
    builder.row(KeyboardButton(text="⚙️ Bot Sozlamalari"))
    builder.row(KeyboardButton(text="🏠 Asosiy menyu"))
    
    return builder.as_markup(resize_keyboard=True)

def get_main_reply_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🏆 Faol konkurslar"))
    builder.row(KeyboardButton(text="📋 Mening ishtiroklarim"), KeyboardButton(text="👥 Referal tizimi"))
    builder.row(KeyboardButton(text="🤖 AI Yordamchi"))
    
    return builder.as_markup(resize_keyboard=True)
