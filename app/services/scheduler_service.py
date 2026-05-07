import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.contest_service import get_contests_ending_soon, select_winners
from app.utils.formatting import format_results_view

logger = logging.getLogger(__name__)


async def check_expired_contests(bot: Bot, session_pool: async_sessionmaker):
    async with session_pool() as session:
        expired = await get_contests_ending_soon(session)
        for contest in expired:
            logger.info("Auto-ending contest #%d: %s", contest.id, contest.title)
            winners = await select_winners(session, contest.id)
            if winners:
                text = format_results_view(contest, winners)
                text += "\n\n\u23f0 Konkurs vaqti tugadi! G'oliblar avtomatik tanlandi."
                try:
                    await bot.send_message(
                        chat_id=contest.created_by,
                        text=text,
                        parse_mode="HTML",
                    )
                except Exception:
                    logger.exception(
                        "Failed to notify admin %d about contest #%d",
                        contest.created_by,
                        contest.id,
                    )


def setup_scheduler(bot: Bot, session_pool: async_sessionmaker) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_expired_contests,
        "interval",
        seconds=30,
        args=[bot, session_pool],
        id="check_expired_contests",
        replace_existing=True,
    )
    return scheduler
