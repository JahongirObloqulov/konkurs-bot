import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import Config
from app.db.engine import create_engine, create_session_pool, init_db
from app.handlers import admin, start, user
from app.middlewares.db_middleware import DbSessionMiddleware

logger = logging.getLogger(__name__)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    config = Config.from_env()

    if not config.bot_token:
        logger.error("BOT_TOKEN topilmadi! .env faylini tekshiring.")
        sys.exit(1)

    engine = create_engine(config.db_url)
    await init_db(engine)
    session_pool = create_session_pool(engine)
    
    # Load settings from database
    async with session_pool() as session:
        from app.services.settings_service import get_required_chats
        db_chats = await get_required_chats(session)
        if db_chats:
            config.required_chats = db_chats
            logger.info(f"Loaded {len(db_chats)} required chats from database")

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware(session_pool=session_pool))
    dp["config"] = config

    dp.include_routers(
        start.router,
        admin.router,
        user.router,
    )

    logger.info("Bot ishga tushdi!")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
