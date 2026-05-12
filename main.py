import asyncio
import logging
import sys
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
import uvicorn
from dotenv import load_dotenv
from sqlalchemy import select

from app.config import Config
from app.db.engine import create_engine, create_session_pool, init_db
from app.handlers import admin, start, user, events, registration
from app.middlewares.db_middleware import DbSessionMiddleware
from web.app import app as web_app

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

load_dotenv()
config = Config.from_env()

if not config.bot_token:
    logger.error("BOT_TOKEN topilmadi! .env faylini tekshiring.")
    sys.exit(1)

# Database setup for Bot
engine = create_engine(config.db_url)
session_pool = create_session_pool(engine)

# Bot Initialization
bot = Bot(
    token=config.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=MemoryStorage())
dp.update.middleware(DbSessionMiddleware(session_pool=session_pool))
dp["config"] = config
dp.include_routers(start.router, registration.router, admin.router, user.router, events.router)

# Attach bot to web_app state for access in routes
web_app.state.bot = bot

async def run_bot():
    from app.db.models import Bot as BotModel
    
    # Initialize list of bots
    bots = []
    
    # 1. Add Master Bot from .env
    master_bot = bot # already initialized at line 39
    bots.append(master_bot)
    
    # 2. Add Active Bots from Database
    async with session_pool() as session:
        from app.services.settings_service import get_required_chats
        db_chats = await get_required_chats(session)
        if db_chats:
            config.required_chats = db_chats
            logger.info(f"Loaded {len(db_chats)} required chats from database")
            
        # Add db_id to Master Bot
        res_master = await session.execute(select(BotModel).where(BotModel.token == config.bot_token))
        master_db = res_master.scalar_one_or_none()
        if master_db:
            master_bot.db_id = master_db.id
            logger.info(f"Master bot DB ID: {master_db.id}")
            
        res = await session.execute(select(BotModel).where(BotModel.is_active == True))
        db_bots = res.scalars().all()
        
        for b_db in db_bots:
            if b_db.token != config.bot_token:
                try:
                    new_bot = Bot(token=b_db.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                    new_bot.db_id = b_db.id # Inject DB ID
                    bots.append(new_bot)
                    b_db.is_running = True
                    logger.info(f"Adding extra bot: @{b_db.username} (DB ID: {b_db.id})")
                except Exception as e:
                    b_db.last_error = str(e)
                    b_db.is_active = False
                    logger.error(f"Error initializing bot {b_db.username}: {e}")
        
        await session.commit()

    logger.info(f"Telegram botlar ishga tushdi! (Jami: {len(bots)})")
    try:
        # Delete webhooks for all bots
        for b in bots:
            await b.delete_webhook(drop_pending_updates=True)
            
        # Start polling for all bots concurrently
        await dp.start_polling(*bots)
    finally:
        for b in bots:
            await b.session.close()
        await engine.dispose()

async def run_web():
    logger.info("Web admin panel ishga tushdi!")
    port = int(os.getenv("PORT", 8000))
    server_config = uvicorn.Config(web_app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(server_config)
    await server.serve()

async def main():
    # Ensure DB is initialized once before everything else
    await init_db(engine)
    
    # Run both concurrently
    await asyncio.gather(
        run_bot(),
        run_web()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot va Web panel to'xtatildi.")
    except Exception as e:
        logger.exception(f"Kutilmagan xatolik: {e}")
