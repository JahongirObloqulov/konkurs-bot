from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.config import Config
from app.keyboards.inline import (
    get_admin_menu_kb,
    get_contest_detail_kb,
    get_contest_list_kb,
    get_main_menu_kb,
    get_subscription_kb,
    get_referral_kb,
)
from app.keyboards.reply import get_main_reply_kb
from app.services.contest_service import (
    add_participant,
    get_active_contests,
    get_contest_by_id,
    get_participants_count,
    get_user_contests,
    get_winners,
    is_participant,
)
from app.services.subscription_service import check_all_subscriptions
from app.utils.formatting import format_contest_view, format_results_view

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "🏆 Faol konkurslar")
async def show_active_contests_reply(message: Message, session: AsyncSession):
    await show_active_contests_core(message, session)

@router.callback_query(F.data == "active_contests")
async def show_active_contests_cb(callback: CallbackQuery, session: AsyncSession):
    await show_active_contests_core(callback.message, session, edit=True)

async def show_active_contests_core(message: Message, session: AsyncSession, edit: bool = False):
    contests = await get_active_contests(session)
    if not contests:
        text = (
            "\U0001f4ed Hozirda faol konkurslar yo'q.\n\n"
            "Yangi konkurslar e'lon qilinishini kuting!"
        )
        if edit:
            await message.edit_text(text, reply_markup=get_main_menu_kb())
        else:
            await message.answer(text)
        return

    text = "\U0001f3c6 <b>Faol konkurslar:</b>\n\nBirini tanlang:"
    kb = get_contest_list_kb(contests)
    if edit:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


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
    kb = get_contest_detail_kb(contest, already_joined)

    if contest.media_type and contest.file_id:
        try:
            # Delete old text message and send new one with media
            await callback.message.delete()
            if contest.media_type == "photo":
                await callback.message.answer_photo(
                    photo=contest.file_id, caption=text, reply_markup=kb, parse_mode="HTML"
                )
            elif contest.media_type == "video":
                await callback.message.answer_video(
                    video=contest.file_id, caption=text, reply_markup=kb, parse_mode="HTML"
                )
            return
        except Exception as e:
            logger.error(f"Failed to send media: {e}")

    await callback.message.edit_text(
        text,
        reply_markup=kb,
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


@router.message(F.text == "👥 Referal tizimi")
async def show_referral_program_reply(message: Message, session: AsyncSession, bot: Bot):
    await show_referral_program_core(message, session, bot)

@router.callback_query(F.data == "referral_program")
async def show_referral_program_cb(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    await show_referral_program_core(callback.message, session, bot, edit=True)

async def show_referral_program_core(message: Message, session: AsyncSession, bot: Bot, edit: bool = False):
    from app.services.user_service import get_user_by_id
    
    user_id = message.chat.id
    user = await get_user_by_id(session, user_id)
    
    if not user:
        return

    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref{user_id}"
    
    text = (
        "\U0001f465 <b>Referal tizimi</b>\n\n"
        "Do'stlaringizni botga taklif qiling va qo'shimcha imkoniyatlarga ega bo'ling!\n\n"
        f"Sizning taklif havolangiz:\n<code>{link}</code>\n\n"
        f"Taklif qilingan do'stlar soni: <b>{user.referral_count}</b>"
    )
    
    kb = get_referral_kb(bot_info.username, user_id)
    
    if edit:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(F.text == "📋 Mening ishtiroklarim")
async def show_my_contests_reply(message: Message, session: AsyncSession):
    await show_my_contests_core(message, session)

@router.callback_query(F.data == "my_contests")
async def show_my_contests_cb(callback: CallbackQuery, session: AsyncSession):
    await show_my_contests_core(callback.message, session, edit=True)

async def show_my_contests_core(message: Message, session: AsyncSession, edit: bool = False):
    user_id = message.chat.id
    contests = await get_user_contests(session, user_id)

    if not contests:
        text = "\U0001f4ed Siz hali hech qanday konkursda ishtirok etmagansiz."
        if edit:
            await message.edit_text(text, reply_markup=get_main_menu_kb())
        else:
            await message.answer(text)
        return

    text = "\U0001f4cb <b>Siz ishtirok etgan konkurslar:</b>"
    kb = get_contest_list_kb(contests)
    if edit:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, config: Config):
    from app.keyboards.reply import get_admin_reply_kb, get_main_reply_kb
    user = callback.from_user
    text = (
        f"Assalomu alaykum, {user.full_name}! \U0001f44b\n\n"
        "\U0001f3c6 <b>Konkurs Bot</b>\n\n"
        "Quyidagi tugmalardan birini tanlang:"
    )
    if config.is_admin(user.id):
        kb = get_admin_reply_kb()
    else:
        kb = get_main_reply_kb()

    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.message.answer("Menyu yangilandi:", reply_markup=kb)


@router.callback_query(F.data == "already_joined")
async def already_joined_handler(callback: CallbackQuery):
    await callback.answer("Siz allaqachon ishtirok etyapsiz!", show_alert=False)


@router.callback_query(F.data.startswith("join_"))
async def join_contest(
    callback: CallbackQuery, session: AsyncSession, config: Config, bot: Bot
):
    from app.services.contest_service import check_requirements
    
    contest_id = int(callback.data.split("_")[1])
    contest = await get_contest_by_id(session, contest_id)
    if not contest or not contest.is_active:
        await callback.answer("Konkurs topilmadi yoki tugagan!", show_alert=True)
        return

    user = callback.from_user

    # 1. Check subscriptions
    if contest.require_subscription:
        all_subscribed, unsubscribed = await check_all_subscriptions(bot, user.id, session)
        if not all_subscribed:
            await callback.message.edit_text(
                "⚠️ <b>Ishtirok etish uchun quyidagi kanallarga/guruhlarga obuna bo'ling!</b>\n\n"
                "Barcha kanallarga obuna bo'lgach, \"Obunani tekshirish\" tugmasini bosing.",
                reply_markup=get_subscription_kb(unsubscribed, contest_id),
                parse_mode="HTML",
            )
            return

    # 2. Check other requirements (referrals, additions)
    meets_reqs, error_msg = await check_requirements(session, contest, user.id)
    if not meets_reqs:
        await callback.message.edit_text(
            f"❌ <b>Siz ushbu konkurs shartlarini hali bajarmagansiz!</b>\n\n"
            f"{error_msg}\n\n"
            "Shartlarni bajarib, qaytadan urinib ko'ring.",
            reply_markup=get_contest_detail_kb(contest, False),
            parse_mode="HTML"
        )
        return

    result = await _join_contest_core(session, contest_id, user)
    if not result:
        await callback.answer("Konkurs topilmadi yoki tugagan!", show_alert=True)
        return

    contest, joined_now, participants_count = result
    await callback.answer(
        (
            f"✅ Siz muvaffaqiyatli ro'yxatdan o'tdingiz! (Jami: {participants_count})"
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

    all_subscribed, unsubscribed = await check_all_subscriptions(bot, user.id, session)
    if not all_subscribed:
        await callback.answer(
            "❌ Hali barcha kanallarga obuna bo'lmagansiz! Iltimos, avval obuna bo'ling.",
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
            f"✅ Siz muvaffaqiyatli ro'yxatdan o'tdingiz! (Jami: {participants_count})"
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
