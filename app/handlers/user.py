from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Config
from app.keyboards.inline import (
    get_contest_detail_kb,
    get_contest_list_kb,
    get_main_menu_kb,
    get_subscription_kb,
)
from app.services.contest_service import (
    add_participant,
    get_active_contests,
    get_contest_by_id,
    get_participants_count,
    get_user_contests,
    get_winners,
    is_participant,
)
from app.services.subscription_service import check_subscription
from app.utils.formatting import format_contest_view, format_results_view

router = Router()


@router.callback_query(F.data == "active_contests")
async def show_active_contests(callback: CallbackQuery, session: AsyncSession):
    contests = await get_active_contests(session)
    if not contests:
        await callback.message.edit_text(
            "\U0001f4ed Hozirda faol konkurslar yo'q.\n\n"
            "Yangi konkurslar e'lon qilinishini kuting!",
            reply_markup=get_main_menu_kb(),
        )
        return

    await callback.message.edit_text(
        "\U0001f3c6 <b>Faol konkurslar:</b>\n\nBirini tanlang:",
        reply_markup=get_contest_list_kb(contests),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("contest_"))
async def show_contest_detail(
    callback: CallbackQuery, session: AsyncSession, config: Config
):
    contest_id = int(callback.data.split("_")[1])
    contest = await get_contest_by_id(session, contest_id)
    if not contest:
        await callback.answer("Konkurs topilmadi!", show_alert=True)
        return

    user_id = callback.from_user.id
    already_joined = await is_participant(session, contest_id, user_id)
    participants_count = await get_participants_count(session, contest_id)
    text = format_contest_view(contest, participants_count)

    await callback.message.edit_text(
        text,
        reply_markup=get_contest_detail_kb(contest, already_joined),
        parse_mode="HTML",
    )


async def _join_contest_core(
    session: AsyncSession, contest_id: int, user
) -> tuple | None:
    contest = await get_contest_by_id(session, contest_id)
    if not contest or not contest.is_active:
        return None

    participant = await add_participant(
        session,
        contest_id=contest_id,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )
    participants_count = await get_participants_count(session, contest_id)
    joined_now = participant is not None
    return contest, joined_now, participants_count


@router.callback_query(F.data.startswith("join_"))
async def join_contest(
    callback: CallbackQuery, session: AsyncSession, config: Config, bot: Bot
):
    contest_id = int(callback.data.split("_")[1])
    contest = await get_contest_by_id(session, contest_id)
    if not contest or not contest.is_active:
        await callback.answer("Konkurs topilmadi yoki tugagan!", show_alert=True)
        return

    user = callback.from_user

    if contest.require_subscription and config.channel_id:
        is_subscribed = await check_subscription(bot, config.channel_id, user.id)
        if not is_subscribed:
            await callback.message.edit_text(
                "\u26a0\ufe0f <b>Ishtirok etish uchun kanalimizga obuna bo'ling!</b>\n\n"
                "Quyidagi tugmani bosib kanalga obuna bo'ling, "
                "so'ng \"Obunani tekshirish\" tugmasini bosing.",
                reply_markup=get_subscription_kb(config.channel_username, contest_id),
                parse_mode="HTML",
            )
            return

    result = await _join_contest_core(session, contest_id, user)
    if not result:
        await callback.answer("Konkurs topilmadi yoki tugagan!", show_alert=True)
        return

    contest, joined_now, participants_count = result
    await callback.answer(
        (
            f"\u2705 Siz muvaffaqiyatli ro'yxatdan o'tdingiz! (Jami: {participants_count})"
            if joined_now
            else "Siz allaqachon ushbu konkursda ishtirok etyapsiz!"
        ),
        show_alert=True,
    )

    text = format_contest_view(contest, participants_count)
    await callback.message.edit_text(
        text,
        reply_markup=get_contest_detail_kb(contest, True),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("check_sub_"))
async def check_subscription_callback(
    callback: CallbackQuery, session: AsyncSession, config: Config, bot: Bot
):
    contest_id = int(callback.data.split("_")[2])
    user = callback.from_user

    if not config.channel_id:
        await callback.answer(
            "Kanal sozlanmagan. Administrator bilan bog'laning.",
            show_alert=True,
        )
        return

    is_subscribed = await check_subscription(bot, config.channel_id, user.id)
    if not is_subscribed:
        await callback.answer(
            "\u274c Siz hali kanalga obuna bo'lmagansiz! Iltimos, avval obuna bo'ling.",
            show_alert=True,
        )
        return

    result = await _join_contest_core(session, contest_id, user)
    if not result:
        await callback.answer("Konkurs topilmadi yoki tugagan!", show_alert=True)
        return

    contest, joined_now, participants_count = result
    await callback.answer(
        (
            f"\u2705 Siz muvaffaqiyatli ro'yxatdan o'tdingiz! (Jami: {participants_count})"
            if joined_now
            else "Siz allaqachon ushbu konkursda ishtirok etyapsiz!"
        ),
        show_alert=True,
    )

    text = format_contest_view(contest, participants_count)
    await callback.message.edit_text(
        text,
        reply_markup=get_contest_detail_kb(contest, True),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("results_"))
async def show_results(callback: CallbackQuery, session: AsyncSession):
    contest_id = int(callback.data.split("_")[1])
    contest = await get_contest_by_id(session, contest_id)
    if not contest:
        await callback.answer("Konkurs topilmadi!", show_alert=True)
        return

    winners = await get_winners(session, contest_id)
    if not winners:
        await callback.answer("G'oliblar hali tanlanmagan!", show_alert=True)
        return

    text = format_results_view(contest, winners)
    await callback.message.edit_text(
        text,
        reply_markup=get_contest_detail_kb(contest, False),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "my_contests")
async def show_my_contests(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    contests = await get_user_contests(session, user_id)

    if not contests:
        await callback.message.edit_text(
            "\U0001f4ed Siz hali hech qanday konkursda ishtirok etmagansiz.",
            reply_markup=get_main_menu_kb(),
        )
        return

    await callback.message.edit_text(
        "\U0001f4cb <b>Siz ishtirok etgan konkurslar:</b>",
        reply_markup=get_contest_list_kb(contests),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, config: Config):
    user = callback.from_user
    text = (
        f"Assalomu alaykum, {user.full_name}! \U0001f44b\n\n"
        "\U0001f3c6 <b>Konkurs Bot</b>\n\n"
        "Quyidagi tugmalardan birini tanlang:"
    )
    if config.is_admin(user.id):
        from app.keyboards.inline import get_admin_menu_kb

        kb = get_admin_menu_kb()
    else:
        kb = get_main_menu_kb()

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "already_joined")
async def already_joined_handler(callback: CallbackQuery):
    await callback.answer("Siz allaqachon ishtirok etyapsiz!", show_alert=False)
