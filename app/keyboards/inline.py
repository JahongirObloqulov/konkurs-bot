from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.models import Contest


def get_main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="\U0001f3c6 Faol konkurslar", callback_data="active_contests"
        )
    )
    builder.row(
        InlineKeyboardButton(text="\U0001f4cb Mening ishtiroklarim", callback_data="my_contests")
    )
    builder.row(
        InlineKeyboardButton(text="\U0001f465 Referal tizimi", callback_data="referral_program")
    )
    return builder.as_markup()


def get_admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="➕ Konkurs yaratish", callback_data="create_contest"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Barcha konkurslar", callback_data="admin_all_contests"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📢 Kanal/Guruh boshqaruvi", callback_data="manage_chats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📊 Statistika", callback_data="admin_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📢 Xabar tarqatish", callback_data="admin_broadcast"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")
    )
    return builder.as_markup()


def get_contest_list_kb(
    contests: list[Contest], prefix: str = "contest"
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for contest in contests:
        status = "\u2705" if contest.is_active else "\u274c"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {contest.title}",
                callback_data=f"{prefix}_{contest.id}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="\U0001f519 Orqaga", callback_data="back_to_main")
    )
    return builder.as_markup()


def get_contest_detail_kb(
    contest: Contest, is_participant: bool = False
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if contest.is_active and not is_participant:
        builder.row(
            InlineKeyboardButton(
                text="\u2705 Ishtirok etish",
                callback_data=f"join_{contest.id}",
            )
        )
    elif is_participant:
        builder.row(
            InlineKeyboardButton(
                text="\u2705 Siz allaqachon ishtirok etyapsiz",
                callback_data="already_joined",
            )
        )
    if not contest.is_active:
        builder.row(
            InlineKeyboardButton(
                text="\U0001f3c6 Natijalarni ko'rish",
                callback_data=f"results_{contest.id}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="\U0001f519 Orqaga", callback_data="active_contests")
    )
    return builder.as_markup()


def get_admin_contest_kb(contest: Contest) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if contest.is_active:
        builder.row(
            InlineKeyboardButton(
                text="\U0001f3b2 G'oliblarni tanlash",
                callback_data=f"pick_winners_{contest.id}",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="\u23f9 Konkursni tugatish",
                callback_data=f"end_contest_{contest.id}",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="\U0001f3c6 Natijalar",
                callback_data=f"results_{contest.id}",
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="\U0001f4ca Ishtirokchilar",
            callback_data=f"participants_{contest.id}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="\U0001f5d1 O'chirish",
            callback_data=f"delete_contest_{contest.id}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="\U0001f519 Orqaga", callback_data="admin_all_contests"
        )
    )
    return builder.as_markup()


def get_confirm_kb(action: str, contest_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="\u2705 Ha, tasdiqlash",
            callback_data=f"confirm_{action}_{contest_id}",
        ),
        InlineKeyboardButton(
            text="\u274c Bekor qilish",
            callback_data=f"cancel_{action}_{contest_id}",
        ),
    )
    return builder.as_markup()


def get_subscription_kb(unsubscribed_chats: list[dict], contest_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for chat in unsubscribed_chats:
        chat_username = chat.get("username", "")
        chat_name = f"Kanalga obuna bo'lish" if chat.get("type") == "channel" else f"Guruhga qo'shilish"
        if chat_username:
            builder.row(
                InlineKeyboardButton(
                    text=f"📢 {chat_name}",
                    url=f"https://t.me/{chat_username.lstrip('@')}",
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text=f"📢 {chat_name} (ID: {chat['id']})",
                    url=f"https://t.me/c/{str(chat['id']).replace('-100', '')}",
                )
            )
    builder.row(
        InlineKeyboardButton(
            text="✅ Obunani tekshirish",
            callback_data=f"check_sub_{contest_id}",
        )
    )
    if contest_id == 0:  # Start-up registration case
        builder.row(
            InlineKeyboardButton(
                text="📝 Ro'yxatdan o'tish", callback_data="start_registration"
            )
        )
    return builder.as_markup()


def get_skip_subscription_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⏩ O'tkazib yuborish (obunasiz)",
            callback_data="skip_subscription",
        )
    )
    return builder.as_markup()


def get_winners_count_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in [1, 2, 3, 5, 10]:
        builder.add(
            InlineKeyboardButton(text=str(i), callback_data=f"winners_count_{i}")
        )
    builder.adjust(5)
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_create")
    )
    return builder.as_markup()


def get_subscription_toggle_kb(require: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔄 Obunasiz qilish" if require else "🔄 Obuna shart qilish",
            callback_data=f"toggle_sub_{'off' if require else 'on'}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="➡️ Davom etish",
            callback_data="confirm_create",
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_create")
    )
    return builder.as_markup()


def get_chat_manage_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="➕ Kanal/Guruh qo'shish",
            callback_data="add_chat",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Admin menyu",
            callback_data="back_to_admin_menu",
        )
    )
    return builder.as_markup()


def get_chat_list_kb(chats: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for chat in chats:
        chat_type = "📢" if chat.get("type") == "channel" else "👥"
        username = chat.get("username", "no_username")
        builder.row(
            InlineKeyboardButton(
                text=f"{chat_type} @{username} ({chat['id']})",
                callback_data=f"chat_detail_{chat['id']}",
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="➕ Qo'shish",
            callback_data="add_chat",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Admin menyu",
            callback_data="back_to_admin_menu",
        )
    )
    return builder.as_markup()


def get_chat_detail_kb(chat_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="\U0001f5d1 O'chirish",
            callback_data=f"remove_chat_{chat_id}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="manage_chats",
        )
    )
    return builder.as_markup()


def get_chat_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📢 Kanal",
            callback_data="chat_type_channel",
        ),
        InlineKeyboardButton(
            text="👥 Guruh",
            callback_data="chat_type_group",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Bekor qilish",
            callback_data="cancel_add_chat",
        )
    )
    return builder.as_markup()


def get_back_to_chats_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="back_to_chats",
        )
    )
    return builder.as_markup()


def get_referral_kb(bot_username: str, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    ref_link = f"https://t.me/{bot_username}?start=ref{user_id}"
    builder.row(
        InlineKeyboardButton(
            text="\U0001f517 Havolani nusxalash",
            url=f"https://t.me/share/url?url={ref_link}&text=Ushbu bot orqali konkurslarda ishtirok eting va sovg'alar yuting!"
        )
    )
    builder.row(
        InlineKeyboardButton(text="\U0001f519 Orqaga", callback_data="back_to_main")
    )
    return builder.as_markup()


def get_requirement_settings_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="0", callback_data="set_req_0"),
        InlineKeyboardButton(text="1", callback_data="set_req_1"),
        InlineKeyboardButton(text="3", callback_data="set_req_3"),
        InlineKeyboardButton(text="5", callback_data="set_req_5"),
        InlineKeyboardButton(text="10", callback_data="set_req_10"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_create")
    )
    return builder.as_markup()
