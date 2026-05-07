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
from app.services.user_service import get_users_count

router = Router()


class CreateContestState(StatesGroup):
    title = State()
    description = State()
    prize = State()
    winners_count = State()
    require_subscription = State()


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
    data = await state.get_data()
    data["require_subscription"] = False
    await _finish_create_contest(callback, state, session, data)


@router.callback_query(
    CreateContestState.require_subscription,
    F.data == "confirm_create",
    admin_check,
)
async def confirm_create(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    data = await state.get_data()
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
    status = "\u2705 Faol" if contest.is_active else "\u274c Tugagan"
    sub_status = "\u2705 Ha" if contest.require_subscription else "\u274c Yo'q"

    text = (
        f"\U0001f3c6 <b>{contest.title}</b>\n\n"
        f"\U0001f4dd {contest.description}\n\n"
        f"\U0001f381 <b>Sovg'a:</b> {contest.prize}\n"
        f"\U0001f465 <b>Ishtirokchilar:</b> {participants_count}\n"
        f"\U0001f3c5 <b>G'oliblar soni:</b> {contest.winners_count}\n"
        f"\U0001f4e2 <b>Obuna shart:</b> {sub_status}\n"
        f"\U0001f4ca <b>Holat:</b> {status}\n"
    )

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

    text = f"\U0001f389 <b>{contest.title} - Natijalar!</b>\n\n\U0001f3c5 <b>G'oliblar:</b>\n\n"
    for i, winner in enumerate(winners, 1):
        mention = f"@{winner.username}" if winner.username else winner.full_name
        text += f"{i}. {mention} ({winner.full_name})\n"

    text += f"\n\U0001f381 <b>Sovg'a:</b> {contest.prize}\n\n\U0001f389 Tabriklaymiz!"

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
        text += f"{i}. {mention} ({p.full_name})\n"

    text += f"\n<b>Jami: {len(participants)} ta</b>"

    await callback.message.edit_text(
        text, reply_markup=get_admin_contest_kb(contest), parse_mode="HTML"
    )
