from aiogram import Bot, Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.contest_service import get_active_contests, get_participants_count

router = Router()


@router.inline_query()
async def inline_contests(inline_query: InlineQuery, session: AsyncSession, bot: Bot):
    contests = await get_active_contests(session)
    bot_info = await bot.get_me()

    results = []
    for contest in contests[:20]:
        participants_count = await get_participants_count(session, contest.id)
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{contest.id}_{inline_query.from_user.id}"

        text = (
            f"\U0001f3c6 <b>{contest.title}</b>\n\n"
            f"\U0001f4dd {contest.description}\n\n"
            f"\U0001f381 <b>Sovg'a:</b> {contest.prize}\n"
            f"\U0001f465 <b>Ishtirokchilar:</b> {participants_count}\n"
            f"\U0001f3c5 <b>G'oliblar soni:</b> {contest.winners_count}\n\n"
            f"\U0001f449 <b>Ishtirok etish:</b> {ref_link}"
        )

        results.append(
            InlineQueryResultArticle(
                id=str(contest.id),
                title=f"\U0001f3c6 {contest.title}",
                description=f"\U0001f381 {contest.prize} | \U0001f465 {participants_count} ishtirokchi",
                input_message_content=InputTextMessageContent(
                    message_text=text,
                    parse_mode="HTML",
                ),
            )
        )

    if not results:
        results.append(
            InlineQueryResultArticle(
                id="no_contests",
                title="\U0001f4ed Faol konkurslar yo'q",
                description="Hozirda faol konkurslar mavjud emas",
                input_message_content=InputTextMessageContent(
                    message_text="\U0001f4ed Hozirda faol konkurslar yo'q.",
                ),
            )
        )

    await inline_query.answer(results, cache_time=30)
