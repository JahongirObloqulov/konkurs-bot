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
    return builder.as_markup()


def get_admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="\u2795 Konkurs yaratish", callback_data="create_contest"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="\U0001f4cb Barcha konkurslar", callback_data="admin_all_contests"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="\U0001f4ca Statistika", callback_data="admin_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(text="\U0001f519 Orqaga", callback_data="back_to_main")
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


def get_subscription_kb(channel_username: str, contest_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="\U0001f4e2 Kanalga obuna bo'lish",
            url=f"https://t.me/{channel_username.lstrip('@')}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="\u2705 Obunani tekshirish",
            callback_data=f"check_sub_{contest_id}",
        )
    )
    return builder.as_markup()


def get_skip_subscription_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="\u23e9 O'tkazib yuborish (obunasiz)",
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
        InlineKeyboardButton(text="\u274c Bekor qilish", callback_data="cancel_create")
    )
    return builder.as_markup()


def get_subscription_toggle_kb(require: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="\U0001f504 Obunasiz qilish" if require else "\U0001f504 Obuna shart qilish",
            callback_data=f"toggle_sub_{'off' if require else 'on'}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="\u27a1\ufe0f Davom etish",
            callback_data="confirm_create",
        )
    )
    builder.row(
        InlineKeyboardButton(text="\u274c Bekor qilish", callback_data="cancel_create")
    )
    return builder.as_markup()
