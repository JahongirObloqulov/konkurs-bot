from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Config
from app.keyboards.inline import (
    get_admin_contest_kb,
    get_admin_menu_kb,
    get_confirm_kb,
    get_contest_list_kb,
    get_subscription_toggle_kb,
    get_timer_kb,
    get_winners_count_kb,
)
from app.services.contest_service import (
    create_contest,
    delete_contest,
    end_contest,
    get_all_contests,
    get_contest_by_id,
    get_participants,
    get_participants_count,
    get_referral_count,
    get_winners,
    select_winners,
)
from app.services.user_service import get_all_users, get_users_count
from app.utils.formatting import format_contest_view, format_results_view

router = Router()


class CreateContestState(StatesGroup):
    title = State()
    description = State()
    prize = State()
    media = State()
    winners_count = State()
    require_subscription = State()
    timer = State()
    custom_timer = State()


class BroadcastState(StatesGroup):
    message = State()


def admin_check(callback: CallbackQuery, config: Config) -> bool:
    return config.is_admin(callback.from_user.id)


def admin_message_check(message: Message, config: Config) -> bool:
    return message.from_user is not None and config.is_admin(message.from_user.id)


# ===== Admin Menu =====


@router.callback_query(F.data == "admin_stats", admin_check)
async def show_stats(callback: CallbackQuery, session: AsyncSession):
    from app.services.contest_service import get_active_contests

    active = await get_active_contests(session)
    all_contests = await get_all_contests(session)
    users_count = await get_users_count(session)

    text = (
        "\U0001f4ca <b>Bot statistikasi</b>\n\n"
        f"\U0001f465 Foydalanuvchilar: {users_count}\n"
        f"\U0001f3c6 Jami konkurslar: {len(all_contests)}\n"
        f"\u2705 Faol konkurslar: {len(active)}\n"
        f"\u274c Tugagan konkurslar: {len(all_contests) - len(active)}\n"
    )

    await callback.message.edit_text(
        text, reply_markup=get_admin_menu_kb(), parse_mode="HTML"
    )


# ===== Create Contest =====


@router.callback_query(F.data == "create_contest", admin_check)
async def start_create_contest(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateContestState.title)
    await callback.message.edit_text(
        "\u2795 <b>Yangi konkurs yaratish</b>\n\n"
        "\U0001f4dd Konkurs nomini yozing:",
        parse_mode="HTML",
    )


@router.message(CreateContestState.title, admin_message_check)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer(
        "\U0001f4dd Konkurs tavsifini yozing:\n\n"
        "<i>(Konkurs haqida batafsil ma'lumot)</i>",
        parse_mode="HTML",
    )
    await state.set_state(CreateContestState.description)


@router.message(CreateContestState.description, admin_message_check)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer(
        "\U0001f381 Sovg'ani yozing:\n\n"
        "<i>(G'olibga beriladigan sovg'a)</i>",
        parse_mode="HTML",
    )
    await state.set_state(CreateContestState.prize)


@router.message(CreateContestState.prize, admin_message_check)
async def process_prize(message: Message, state: FSMContext):
    await state.update_data(prize=message.text)
    await message.answer(
        "\U0001f4f7 Konkurs uchun rasm yoki video yuboring:\n\n"
        "<i>(Ixtiyoriy — o'tkazib yuborish uchun \"O'tkazib yuborish\" tugmasini bosing)</i>",
        parse_mode="HTML",
        reply_markup=get_timer_kb(skip_text="\u23e9 O'tkazib yuborish", skip_data="skip_media"),
    )
    await state.set_state(CreateContestState.media)


@router.message(CreateContestState.media, admin_message_check)
async def process_media(message: Message, state: FSMContext):
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        media_type = "video"
    elif message.animation:
        file_id = message.animation.file_id
        media_type = "animation"
    elif message.document:
        file_id = message.document.file_id
        media_type = "document"
    else:
        await message.answer(
            "\u26a0\ufe0f Iltimos, rasm, video yoki GIF yuboring.\n"
            "Yoki \"O'tkazib yuborish\" tugmasini bosing.",
        )
        return

    await state.update_data(media_file_id=file_id, media_type=media_type)
    await message.answer(
        "\U0001f3c5 G'oliblar sonini tanlang:",
        reply_markup=get_winners_count_kb(),
    )
    await state.set_state(CreateContestState.winners_count)


@router.callback_query(CreateContestState.media, F.data == "skip_media", admin_check)
async def skip_media(callback: CallbackQuery, state: FSMContext):
    await state.update_data(media_file_id=None, media_type=None)
    await callback.message.edit_text(
        "\U0001f3c5 G'oliblar sonini tanlang:",
        reply_markup=get_winners_count_kb(),
    )
    await state.set_state(CreateContestState.winners_count)


@router.callback_query(
    CreateContestState.winners_count, F.data.startswith("winners_count_"), admin_check
)
async def process_winners_count(callback: CallbackQuery, state: FSMContext):
    count = int(callback.data.split("_")[2])
    await state.update_data(winners_count=count)
    await callback.message.edit_text(
        "\U0001f4e2 Kanalga obuna bo'lish shartmi?\n\n"
        "Hozirgi holat: <b>Ha, obuna shart</b>",
        reply_markup=get_subscription_toggle_kb(True),
        parse_mode="HTML",
    )
    await state.update_data(require_subscription=True)
    await state.set_state(CreateContestState.require_subscription)


@router.callback_query(
    CreateContestState.require_subscription,
    F.data.startswith("toggle_sub_"),
    admin_check,
)
async def toggle_subscription(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[2]
    require = action == "on"
    await state.update_data(require_subscription=require)

    status = "Ha, obuna shart" if require else "Yo'q, obuna shart emas"
    await callback.message.edit_text(
        f"\U0001f4e2 Kanalga obuna bo'lish shartmi?\n\n"
        f"Hozirgi holat: <b>{status}</b>",
        reply_markup=get_subscription_toggle_kb(require),
        parse_mode="HTML",
    )


@router.callback_query(
    CreateContestState.require_subscription,
    F.data == "skip_subscription",
    admin_check,
)
async def skip_subscription(callback: CallbackQuery, state: FSMContext):
    await state.update_data(require_subscription=False)
    await callback.message.edit_text(
        "\u23f0 <b>Konkurs uchun vaqt limiti belgilang:</b>\n\n"
        "Quyidagi variantlardan birini tanlang yoki o'tkazib yuboring:",
        reply_markup=get_timer_kb(),
        parse_mode="HTML",
    )
    await state.set_state(CreateContestState.timer)


@router.callback_query(
    CreateContestState.require_subscription,
    F.data == "confirm_create",
    admin_check,
)
async def confirm_after_subscription(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.edit_text(
        "\u23f0 <b>Konkurs uchun vaqt limiti belgilang:</b>\n\n"
        "Quyidagi variantlardan birini tanlang yoki o'tkazib yuboring:",
        reply_markup=get_timer_kb(),
        parse_mode="HTML",
    )
    await state.set_state(CreateContestState.timer)


@router.callback_query(CreateContestState.timer, F.data.startswith("timer_"), admin_check)
async def process_timer(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    timer_value = callback.data.split("_")[1]

    if timer_value == "none":
        await state.update_data(end_time=None)
        data = await state.get_data()
        await _finish_create_contest(callback, state, session, data)
        return

    if timer_value == "custom":
        await callback.message.edit_text(
            "\u23f0 <b>Vaqt limitini soat sifatida yozing:</b>\n\n"
            "<i>(Masalan: 2, 12, 48, 72)</i>",
            parse_mode="HTML",
        )
        await state.set_state(CreateContestState.custom_timer)
        return

    hours = int(timer_value)
    end_time = datetime.now(timezone.utc) + timedelta(hours=hours)
    await state.update_data(end_time=end_time.isoformat())
    data = await state.get_data()
    await _finish_create_contest(callback, state, session, data)


@router.message(CreateContestState.custom_timer, admin_message_check)
async def process_custom_timer(message: Message, state: FSMContext, session: AsyncSession):
    try:
        hours = float(message.text.strip())
        if hours <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "\u26a0\ufe0f Iltimos, musbat son kiriting (masalan: 2, 12, 48)."
        )
        return

    end_time = datetime.now(timezone.utc) + timedelta(hours=hours)
    await state.update_data(end_time=end_time.isoformat())
    data = await state.get_data()
    await _finish_create_contest_from_message(message, state, session, data)


async def _finish_create_contest(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    data: dict,
):
    end_time = None
    if data.get("end_time"):
        end_time = datetime.fromisoformat(data["end_time"])

    contest = await create_contest(
        session,
        title=data["title"],
        description=data["description"],
        prize=data["prize"],
        winners_count=data["winners_count"],
        created_by=callback.from_user.id,
        require_subscription=data.get("require_subscription", True),
        media_file_id=data.get("media_file_id"),
        media_type=data.get("media_type"),
        end_time=end_time,
    )
    await state.clear()

    text = _format_created_contest(contest)

    if contest.media_file_id and contest.media_type:
        await _send_media_with_text(callback.message, contest, text, get_admin_contest_kb(contest))
    else:
        await callback.message.edit_text(
            text, reply_markup=get_admin_contest_kb(contest), parse_mode="HTML"
        )


async def _finish_create_contest_from_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    data: dict,
):
    end_time = None
    if data.get("end_time"):
        end_time = datetime.fromisoformat(data["end_time"])

    contest = await create_contest(
        session,
        title=data["title"],
        description=data["description"],
        prize=data["prize"],
        winners_count=data["winners_count"],
        created_by=message.from_user.id,
        require_subscription=data.get("require_subscription", True),
        media_file_id=data.get("media_file_id"),
        media_type=data.get("media_type"),
        end_time=end_time,
    )
    await state.clear()

    text = _format_created_contest(contest)

    if contest.media_file_id and contest.media_type:
        await _send_media_message(message, contest, text, get_admin_contest_kb(contest))
    else:
        await message.answer(
            text, reply_markup=get_admin_contest_kb(contest), parse_mode="HTML"
        )


def _format_created_contest(contest) -> str:
    sub_status = "\u2705 Ha" if contest.require_subscription else "\u274c Yo'q"
    text = (
        "\u2705 <b>Konkurs muvaffaqiyatli yaratildi!</b>\n\n"
        f"\U0001f4dd <b>Nomi:</b> {contest.title}\n"
        f"\U0001f4cb <b>Tavsif:</b> {contest.description}\n"
        f"\U0001f381 <b>Sovg'a:</b> {contest.prize}\n"
        f"\U0001f3c5 <b>G'oliblar soni:</b> {contest.winners_count}\n"
        f"\U0001f4e2 <b>Obuna shart:</b> {sub_status}\n"
    )
    if contest.media_file_id:
        text += f"\U0001f4f7 <b>Media:</b> Biriktirilgan\n"
    if contest.end_time:
        text += f"\u23f0 <b>Tugash vaqti:</b> {contest.end_time.strftime('%Y-%m-%d %H:%M')} UTC\n"
    return text


async def _send_media_with_text(message, contest, text, reply_markup):
    from aiogram.types import InputMediaPhoto, InputMediaVideo, InputMediaAnimation

    if contest.media_type == "photo":
        await message.answer_photo(
            photo=contest.media_file_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    elif contest.media_type == "video":
        await message.answer_video(
            video=contest.media_file_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    elif contest.media_type == "animation":
        await message.answer_animation(
            animation=contest.media_file_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    else:
        await message.answer_document(
            document=contest.media_file_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )


async def _send_media_message(message, contest, text, reply_markup):
    if contest.media_type == "photo":
        await message.answer_photo(
            photo=contest.media_file_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    elif contest.media_type == "video":
        await message.answer_video(
            video=contest.media_file_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    elif contest.media_type == "animation":
        await message.answer_animation(
            animation=contest.media_file_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    else:
        await message.answer_document(
            document=contest.media_file_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )


@router.callback_query(F.data == "cancel_create", admin_check)
async def cancel_create(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "\u274c Konkurs yaratish bekor qilindi.",
        reply_markup=get_admin_menu_kb(),
    )


# ===== Broadcast =====


@router.callback_query(F.data == "admin_broadcast", admin_check)
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastState.message)
    await callback.message.edit_text(
        "\U0001f4e3 <b>Broadcast xabar</b>\n\n"
        "Barcha foydalanuvchilarga yuboriladigan xabarni yozing:\n\n"
        "<i>(Bekor qilish uchun /cancel yozing)</i>",
        parse_mode="HTML",
    )


@router.message(BroadcastState.message, admin_message_check)
async def process_broadcast(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer(
            "\u274c Broadcast bekor qilindi.",
            reply_markup=get_admin_menu_kb(),
        )
        return

    await state.clear()
    users = await get_all_users(session)
    sent = 0
    failed = 0

    status_msg = await message.answer(
        f"\U0001f4e8 Xabar yuborilmoqda... (0/{len(users)})"
    )

    for user in users:
        try:
            if message.photo:
                await bot.send_photo(
                    chat_id=user.user_id,
                    photo=message.photo[-1].file_id,
                    caption=message.caption or "",
                    parse_mode="HTML",
                )
            elif message.video:
                await bot.send_video(
                    chat_id=user.user_id,
                    video=message.video.file_id,
                    caption=message.caption or "",
                    parse_mode="HTML",
                )
            else:
                await bot.send_message(
                    chat_id=user.user_id,
                    text=message.text or "",
                    parse_mode="HTML",
                )
            sent += 1
        except Exception:
            failed += 1

        if (sent + failed) % 20 == 0:
            try:
                await status_msg.edit_text(
                    f"\U0001f4e8 Xabar yuborilmoqda... ({sent + failed}/{len(users)})"
                )
            except Exception:
                pass

    await status_msg.edit_text(
        f"\u2705 <b>Broadcast tugadi!</b>\n\n"
        f"\U0001f4e8 Yuborildi: {sent}\n"
        f"\u274c Xato: {failed}\n"
        f"\U0001f465 Jami: {len(users)}",
        reply_markup=get_admin_menu_kb(),
        parse_mode="HTML",
    )


# ===== Export CSV =====


@router.callback_query(F.data.startswith("export_csv_"), admin_check)
async def export_participants_csv(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    contest_id = int(callback.data.split("_")[2])
    contest = await get_contest_by_id(session, contest_id)
    if not contest:
        await callback.answer("Konkurs topilmadi!", show_alert=True)
        return

    participants = await get_participants(session, contest_id)
    if not participants:
        await callback.answer("Ishtirokchilar yo'q!", show_alert=True)
        return

    import io
    csv_content = "No,User ID,Username,Full Name,Joined At,Referred By\n"
    for i, p in enumerate(participants, 1):
        username = p.username or ""
        referred = str(p.referred_by) if p.referred_by else ""
        csv_content += f"{i},{p.user_id},{username},{p.full_name},{p.joined_at},{referred}\n"

    from aiogram.types import BufferedInputFile

    file = BufferedInputFile(
        csv_content.encode("utf-8"),
        filename=f"participants_{contest.title}_{contest_id}.csv",
    )
    await bot.send_document(
        chat_id=callback.from_user.id,
        document=file,
        caption=f"\U0001f4ca {contest.title} - Ishtirokchilar ro'yxati",
    )
    await callback.answer("CSV fayl yuborildi!")


# ===== Manage Contests =====


@router.callback_query(F.data == "admin_all_contests", admin_check)
async def show_all_contests(callback: CallbackQuery, session: AsyncSession):
    contests = await get_all_contests(session)
    if not contests:
        await callback.message.edit_text(
            "\U0001f4ed Hali konkurslar yo'q.",
            reply_markup=get_admin_menu_kb(),
        )
        return

    await callback.message.edit_text(
        "\U0001f4cb <b>Barcha konkurslar:</b>",
        reply_markup=get_contest_list_kb(contests, prefix="admin_contest"),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin_contest_"), admin_check)
async def show_admin_contest_detail(
    callback: CallbackQuery, session: AsyncSession
):
    contest_id = int(callback.data.split("_")[2])
    contest = await get_contest_by_id(session, contest_id)
    if not contest:
        await callback.answer("Konkurs topilmadi!", show_alert=True)
        return

    participants_count = await get_participants_count(session, contest_id)
    sub_status = "\u2705 Ha" if contest.require_subscription else "\u274c Yo'q"
    text = format_contest_view(contest, participants_count)
    text += f"\U0001f4e2 <b>Obuna shart:</b> {sub_status}\n"
    if contest.media_file_id:
        text += f"\U0001f4f7 <b>Media:</b> Biriktirilgan\n"
    if contest.end_time:
        text += f"\u23f0 <b>Tugash vaqti:</b> {contest.end_time.strftime('%Y-%m-%d %H:%M')} UTC\n"

    await callback.message.edit_text(
        text, reply_markup=get_admin_contest_kb(contest), parse_mode="HTML"
    )


# ===== Pick Winners =====


@router.callback_query(F.data.startswith("pick_winners_"), admin_check)
async def pick_winners_confirm(callback: CallbackQuery, session: AsyncSession):
    contest_id = int(callback.data.split("_")[2])
    contest = await get_contest_by_id(session, contest_id)
    if not contest:
        await callback.answer("Konkurs topilmadi!", show_alert=True)
        return

    participants_count = await get_participants_count(session, contest_id)
    if participants_count == 0:
        await callback.answer(
            "Ishtirokchilar yo'q! G'olib tanlash mumkin emas.", show_alert=True
        )
        return

    await callback.message.edit_text(
        f"\U0001f3b2 <b>{contest.title}</b> konkursida g'oliblarni tanlashni tasdiqlaysizmi?\n\n"
        f"\U0001f465 Ishtirokchilar: {participants_count}\n"
        f"\U0001f3c5 G'oliblar soni: {contest.winners_count}\n\n"
        "\u26a0\ufe0f Diqqat: Bu amal konkursni tugatadi!",
        reply_markup=get_confirm_kb("pick", contest_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("confirm_pick_"), admin_check)
async def confirm_pick_winners(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
):
    contest_id = int(callback.data.split("_")[2])
    winners = await select_winners(session, contest_id)
    contest = await get_contest_by_id(session, contest_id)

    if not winners or not contest:
        await callback.answer("Xatolik yuz berdi!", show_alert=True)
        return

    text = format_results_view(contest, winners) + "\n\n\U0001f389 Tabriklaymiz!"

    await callback.message.edit_text(
        text, reply_markup=get_admin_contest_kb(contest), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("cancel_pick_"), admin_check)
async def cancel_pick_winners(callback: CallbackQuery, session: AsyncSession):
    contest_id = int(callback.data.split("_")[2])
    contest = await get_contest_by_id(session, contest_id)
    if contest:
        await callback.message.edit_text(
            "\u274c G'olib tanlash bekor qilindi.",
            reply_markup=get_admin_contest_kb(contest),
        )


# ===== End Contest =====


@router.callback_query(F.data.startswith("end_contest_"), admin_check)
async def end_contest_confirm(callback: CallbackQuery, session: AsyncSession):
    contest_id = int(callback.data.split("_")[2])
    contest = await get_contest_by_id(session, contest_id)
    if not contest:
        await callback.answer("Konkurs topilmadi!", show_alert=True)
        return

    await callback.message.edit_text(
        f"\u23f9 <b>{contest.title}</b> konkursini tugatishni tasdiqlaysizmi?",
        reply_markup=get_confirm_kb("end", contest_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("confirm_end_"), admin_check)
async def confirm_end_contest(callback: CallbackQuery, session: AsyncSession):
    contest_id = int(callback.data.split("_")[2])
    contest = await end_contest(session, contest_id)
    if contest:
        await callback.message.edit_text(
            f"\u23f9 <b>{contest.title}</b> konkursi tugatildi.",
            reply_markup=get_admin_contest_kb(contest),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("cancel_end_"), admin_check)
async def cancel_end_contest(callback: CallbackQuery, session: AsyncSession):
    contest_id = int(callback.data.split("_")[2])
    contest = await get_contest_by_id(session, contest_id)
    if contest:
        await callback.message.edit_text(
            "\u274c Konkursni tugatish bekor qilindi.",
            reply_markup=get_admin_contest_kb(contest),
        )


# ===== Delete Contest =====


@router.callback_query(F.data.startswith("delete_contest_"), admin_check)
async def delete_contest_confirm(callback: CallbackQuery, session: AsyncSession):
    contest_id = int(callback.data.split("_")[2])
    contest = await get_contest_by_id(session, contest_id)
    if not contest:
        await callback.answer("Konkurs topilmadi!", show_alert=True)
        return

    await callback.message.edit_text(
        f"\U0001f5d1 <b>{contest.title}</b> konkursini o'chirishni tasdiqlaysizmi?\n\n"
        "\u26a0\ufe0f Bu amal qaytarib bo'lmaydi!",
        reply_markup=get_confirm_kb("delete", contest_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("confirm_delete_"), admin_check)
async def confirm_delete_contest(callback: CallbackQuery, session: AsyncSession):
    contest_id = int(callback.data.split("_")[2])
    success = await delete_contest(session, contest_id)
    if success:
        await callback.message.edit_text(
            "\u2705 Konkurs muvaffaqiyatli o'chirildi.",
            reply_markup=get_admin_menu_kb(),
        )
    else:
        await callback.answer("Xatolik yuz berdi!", show_alert=True)


@router.callback_query(F.data.startswith("cancel_delete_"), admin_check)
async def cancel_delete_contest(callback: CallbackQuery, session: AsyncSession):
    contest_id = int(callback.data.split("_")[2])
    contest = await get_contest_by_id(session, contest_id)
    if contest:
        await callback.message.edit_text(
            "\u274c O'chirish bekor qilindi.",
            reply_markup=get_admin_contest_kb(contest),
        )


# ===== Participants List =====


@router.callback_query(F.data.startswith("participants_"), admin_check)
async def show_participants(callback: CallbackQuery, session: AsyncSession):
    contest_id = int(callback.data.split("_")[1])
    contest = await get_contest_by_id(session, contest_id)
    if not contest:
        await callback.answer("Konkurs topilmadi!", show_alert=True)
        return

    participants = await get_participants(session, contest_id)
    if not participants:
        await callback.answer("Ishtirokchilar yo'q!", show_alert=True)
        return

    text = f"\U0001f465 <b>{contest.title} - Ishtirokchilar</b>\n\n"
    for i, p in enumerate(participants, 1):
        mention = f"@{p.username}" if p.username else p.full_name
        ref_count = await get_referral_count(session, contest_id, p.user_id)
        ref_text = f" [\U0001f517{ref_count}]" if ref_count > 0 else ""
        text += f"{i}. {mention} ({p.full_name}){ref_text}\n"

    text += f"\n<b>Jami: {len(participants)} ta</b>"

    await callback.message.edit_text(
        text, reply_markup=get_admin_contest_kb(contest), parse_mode="HTML"
    )
