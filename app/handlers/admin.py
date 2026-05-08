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
    get_winners,
    select_winners,
)
from app.services.settings_service import (
    get_required_chats,
    set_required_chats,
)
from app.services.user_service import get_users_count
from app.utils.formatting import format_contest_view, format_results_view

router = Router()


class CreateContestState(StatesGroup):
    title = State()
    description = State()
    prize = State()
    winners_count = State()
    require_subscription = State()
    min_referrals = State()
    min_additions = State()


class ChatManageState(StatesGroup):
    chat_id = State()
    chat_username = State()
    chat_type = State()
    edit_mode = State()


def admin_check(callback: CallbackQuery, config: Config) -> bool:
    return config.is_admin(callback.from_user.id)


def admin_message_check(message: Message, config: Config) -> bool:
    return message.from_user is not None and config.is_admin(message.from_user.id)


# ===== Admin Menu =====


@router.callback_query(F.data == "admin_stats", admin_check)
async def show_stats(callback: CallbackQuery, session: AsyncSession):
    from app.services.contest_service import get_active_contests
    from app.services.settings_service import get_required_chats
    from sqlalchemy import func, select
    from app.db.models import Participant, Winner

    active = await get_active_contests(session)
    all_contests = await get_all_contests(session)
    users_count = await get_users_count(session)
    
    # Additional stats
    required_chats = await get_required_chats(session)
    
    total_participants = await session.execute(select(func.count(Participant.id)))
    total_participants = total_participants.scalar_one()
    
    total_winners = await session.execute(select(func.count(Winner.id)))
    total_winners = total_winners.scalar_one()
    
    total_referrals = await session.execute(select(func.sum(User.referral_count)))
    total_referrals = total_referrals.scalar() or 0
    
    total_additions = await session.execute(select(func.sum(User.added_users_count)))
    total_additions = total_additions.scalar() or 0

    text = (
        "\U0001f4ca <b>Bot statistikasi</b>\n\n"
        f"\U0001f465 Foydalanuvchilar: {users_count}\n"
        f"\U0001f3c6 Jami konkurslar: {len(all_contests)}\n"
        f"✅ Faol konkurslar: {len(active)}\n"
        f"❌ Tugagan konkurslar: {len(all_contests) - len(active)}\n"
        f"\U0001f465 Jami ishtirokchilar: {total_participants}\n"
        f"\U0001f3c5 Jami g'oliblar: {total_winners}\n"
        f"\U0001f4e2 Majburiy kanallar: {len(required_chats)}\n"
        f"\U0001f465 Jami takliflar: {total_referrals}\n"
        f"👤 Jami qo'shilganlar: {total_additions}\n"
    )

    await callback.message.edit_text(
        text, reply_markup=get_admin_menu_kb(), parse_mode="HTML"
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
    title = message.text.strip() if message.text else ""
    if not title:
        await message.answer("❌ Nom bo'sh bo'lishi mumkin emas! Qaytadan kiriting:")
        return
    await state.update_data(title=title)
    await message.answer(
        "\U0001f4DD Konkurs tavsifini yozing:\n\n"
        "<i>(Konkurs haqida batafsil ma'lumot)</i>",
        parse_mode="HTML",
    )
    await state.set_state(CreateContestState.description)


@router.message(CreateContestState.description, admin_message_check)
async def process_description(message: Message, state: FSMContext):
    description = message.text.strip() if message.text else ""
    if not description:
        await message.answer("❌ Tavsif bo'sh bo'lishi mumkin emas! Qaytadan kiriting:")
        return
    await state.update_data(description=description)
    await message.answer(
        "\U0001f381 Sovg'ani yozing:\n\n"
        "<i>(G'olibga beriladigan sovg'a)</i>",
        parse_mode="HTML",
    )
    await state.set_state(CreateContestState.prize)


@router.message(CreateContestState.prize, admin_message_check)
async def process_prize(message: Message, state: FSMContext):
    prize = message.text.strip() if message.text else ""
    if not prize:
        await message.answer("❌ Sovg'a nomi bo'sh bo'lishi mumkin emas! Qaytadan kiriting:")
        return
    await state.update_data(prize=prize)
    await message.answer(
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
async def skip_subscription(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    await state.update_data(require_subscription=False)
    await callback.message.edit_text(
        "\U0001f465 Minimal referallar sonini kiriting (0 - shart emas):",
        reply_markup=get_requirement_settings_kb()
    )
    await state.set_state(CreateContestState.min_referrals)


@router.callback_query(
    CreateContestState.require_subscription,
    F.data == "confirm_create",
    admin_check,
)
async def confirm_create(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    await callback.message.edit_text(
        "\U0001f465 Minimal referallar sonini kiriting (0 - shart emas):",
        reply_markup=get_requirement_settings_kb()
    )
    await state.set_state(CreateContestState.min_referrals)


@router.callback_query(CreateContestState.min_referrals, F.data.startswith("set_req_"), admin_check)
async def process_min_referrals(callback: CallbackQuery, state: FSMContext):
    count = int(callback.data.split("_")[2])
    await state.update_data(min_referrals=count)
    await callback.message.edit_text(
        "👥 Guruhlarga qo'shilishi kerak bo'lgan a'zolar sonini kiriting (0 - shart emas):",
        reply_markup=get_requirement_settings_kb()
    )
    await state.set_state(CreateContestState.min_additions)


@router.callback_query(CreateContestState.min_additions, F.data.startswith("set_req_"), admin_check)
async def process_min_additions(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    count = int(callback.data.split("_")[2])
    data = await state.get_data()
    data["min_additions"] = count
    await _finish_create_contest(callback, state, session, data)


async def _finish_create_contest(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    data: dict,
):
    contest = await create_contest(
        session,
        title=data["title"],
        description=data["description"],
        prize=data["prize"],
        winners_count=data["winners_count"],
        created_by=callback.from_user.id,
        require_subscription=data.get("require_subscription", True),
        min_referrals=data.get("min_referrals", 0),
        min_additions=data.get("min_additions", 0),
    )
    await state.clear()

    if not contest:
        await callback.message.edit_text(
            "❌ Konkurs yaratishda xatolik yuz berdi!",
            reply_markup=get_admin_menu_kb(),
        )
        return

    sub_status = "✅ Ha" if contest.require_subscription else "❌ Yo'q"
    text = (
        "✅ <b>Konkurs muvaffaqiyatli yaratildi!</b>\n\n"
        f"📝 <b>Nomi:</b> {contest.title}\n"
        f"📋 <b>Tavsif:</b> {contest.description}\n"
        f"🎁 <b>Sovg'a:</b> {contest.prize}\n"
        f"🏅 <b>G'oliblar soni:</b> {contest.winners_count}\n"
        f"📢 <b>Obuna shart:</b> {sub_status}\n"
        f"👥 <b>Minimal referallar:</b> {contest.min_referrals}\n"
        f"👤 <b>Minimal qo'shilgan a'zolar:</b> {contest.min_additions}\n"
    )

    await callback.message.edit_text(
        text, reply_markup=get_admin_contest_kb(contest), parse_mode="HTML"
    )
    await state.clear()

    sub_status = "\u2705 Ha" if contest.require_subscription else "\u274c Yo'q"
    text = (
        "\u2705 <b>Konkurs muvaffaqiyatli yaratildi!</b>\n\n"
        f"\U0001f4dd <b>Nomi:</b> {contest.title}\n"
        f"\U0001f4cb <b>Tavsif:</b> {contest.description}\n"
        f"\U0001f381 <b>Sovg'a:</b> {contest.prize}\n"
        f"\U0001f3c5 <b>G'oliblar soni:</b> {contest.winners_count}\n"
        f"\U0001f4e2 <b>Obuna shart:</b> {sub_status}\n"
    )

    await callback.message.edit_text(
        text, reply_markup=get_admin_contest_kb(contest), parse_mode="HTML"
    )


@router.callback_query(F.data == "cancel_create", admin_check)
async def cancel_create(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "\u274c Konkurs yaratish bekor qilindi.",
        reply_markup=get_admin_menu_kb(),
    )


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
    else:
        await callback.answer("Xatolik yuz berdi!", show_alert=True)


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
        text += f"{i}. {mention} ({p.full_name})\n"

    text += f"\n<b>Jami: {len(participants)} ta</b>"

    await callback.message.edit_text(
        text, reply_markup=get_admin_contest_kb(contest), parse_mode="HTML"
    )


# ===== Chat Management =====


@router.callback_query(F.data == "manage_chats", admin_check)
async def show_chat_management(callback: CallbackQuery, session: AsyncSession):
    from app.keyboards.inline import get_chat_list_kb, get_chat_manage_kb
    
    chats = await get_required_chats(session)
    text = "\U0001f4e2 <b>Majburiy obuna kanallari/gruhlari</b>\n\n"
    
    if not chats:
        text += "Hozircha kanallar mavjud emas.\n"
        kb = get_chat_manage_kb()
    else:
        for i, chat in enumerate(chats, 1):
            chat_type = "📢 Kanal" if chat.get("type") == "channel" else "👥 Guruh"
            username = chat.get("username", "Noma'lum")
            text += f"{i}. {chat_type} - @{username} (ID: {chat['id']})\n"
        text += "\n❗ <i>Biror kanalni o'chirish uchun ustiga bosing</i>"
        kb = get_chat_list_kb(chats)
    
    await callback.message.edit_text(
        text, reply_markup=kb, parse_mode="HTML"
    )


@router.callback_query(F.data == "add_chat", admin_check)
async def start_add_chat(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChatManageState.chat_id)
    await callback.message.edit_text(
        "\U0001f4e2 <b>Yangi kanal/guruh qo'shish</b>\n\n"
        "Kanal yoki guruh ID raqamini kiriting:\n\n"
        "<i>Masalan: -1001234567890</i>\n\n"
        "ID ni olish uchun @username_to_id_bot dan foydalaning.",
        parse_mode="HTML",
    )


@router.message(ChatManageState.chat_id, admin_message_check)
async def process_chat_id(message: Message, state: FSMContext):
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID formati! Qaytadan kiriting:")
        return
    
    await state.update_data(chat_id=chat_id)
    await message.answer(
        "Kanal/guruh username ini kiriting (ixtiyoriy):\n\n"
        "<i>Masalan: @my_channel</i>\n\n"
        "Agar username bo'lmasa, '-' belgisini yuboring.",
        parse_mode="HTML",
    )
    await state.set_state(ChatManageState.chat_username)


@router.message(ChatManageState.chat_username, admin_message_check)
async def process_chat_username(message: Message, state: FSMContext):
    username = message.text.strip()
    if username == "-":
        username = ""
    await state.update_data(chat_username=username)
    await message.answer(
        "Kanal turini tanlang:",
        reply_markup=get_chat_type_kb(),
    )
    await state.set_state(ChatManageState.chat_type)


@router.callback_query(
    ChatManageState.chat_type, F.data.startswith("chat_type_"), admin_check
)
async def process_chat_type(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    chat_type = callback.data.split("_")[2]
    data = await state.get_data()
    
    new_chat = {
        "id": data["chat_id"],
        "username": data.get("chat_username", ""),
        "type": chat_type,
    }
    
    chats = await get_required_chats(session)
    chats.append(new_chat)
    
    success = await set_required_chats(session, chats)
    await state.clear()
    
    if success:
        await callback.message.edit_text(
            f"✅ Kanal/Guruh muvaffaqiyatli qo'shildi!\n\n"
            f"ID: {new_chat['id']}\n"
            f"Username: @{new_chat.get('username') or 'yoq'}\n"
            f"Turi: {'Kanal' if chat_type == 'channel' else 'Guruh'}",
            reply_markup=get_back_to_chats_kb(),
            parse_mode="HTML",
        )
    else:
        await callback.answer("Xatolik yuz berdi!", show_alert=True)


@router.callback_query(F.data.startswith("chat_detail_"), admin_check)
async def chat_detail(callback: CallbackQuery, session: AsyncSession):
    from app.keyboards.inline import get_chat_detail_kb
    chat_id = int(callback.data.split("_")[2])
    chats = await get_required_chats(session)
    chat = next((c for c in chats if c["id"] == chat_id), None)
    
    if not chat:
        await callback.answer("Chat topilmadi!", show_alert=True)
        return
        
    chat_type = "📢 Kanal" if chat.get("type") == "channel" else "👥 Guruh"
    text = (
        f"<b>Kanal/Guruh ma'lumotlari:</b>\n\n"
        f"ID: <code>{chat['id']}</code>\n"
        f"Username: @{chat.get('username') or 'yoq'}\n"
        f"Turi: {chat_type}"
    )
    
    await callback.message.edit_text(
        text, reply_markup=get_chat_detail_kb(chat_id), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("remove_chat_"), admin_check)
async def remove_chat(callback: CallbackQuery, session: AsyncSession):
    chat_id = int(callback.data.split("_")[2])
    chats = await get_required_chats(session)
    chats = [c for c in chats if c["id"] != chat_id]
    
    success = await set_required_chats(session, chats)
    if success:
        await callback.answer("✅ Kanal o'chirildi!", show_alert=True)
        await show_chat_management(callback, session)
    else:
        await callback.answer("Xatolik yuz berdi!", show_alert=True)


@router.callback_query(F.data == "back_to_chats", admin_check)
async def back_to_chats(callback: CallbackQuery, session: AsyncSession):
    await show_chat_management(callback, session)


@router.callback_query(F.data == "back_to_admin_menu", admin_check)
async def back_to_admin_menu(callback: CallbackQuery):
    from app.keyboards.inline import get_admin_menu_kb
    
    await callback.message.edit_text(
        "\U0001f6e0 <b>Admin panel</b>\n\n"
        "Quyidagi amallardan birini tanlang:",
        reply_markup=get_admin_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "cancel_add_chat", admin_check)
async def cancel_add_chat(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await state.clear()
    await show_chat_management(callback, session)
