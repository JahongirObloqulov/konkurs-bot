import asyncio
import logging
import sys
import os
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
from dotenv import load_dotenv

from app.config import Config
from app.db.engine import create_engine, create_session_pool, init_db
from app.handlers import admin, start, user, events
from app.middlewares.db_middleware import DbSessionMiddleware

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

# Database setup
engine = create_engine(config.db_url)
session_pool = create_session_pool(engine)

# Web app setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs when the web server starts
    await init_db(engine)
    
    # Load settings from database for the bot config
    async with session_pool() as session:
        from app.services.settings_service import get_required_chats
        db_chats = await get_required_chats(session)
        if db_chats:
            config.required_chats = db_chats
            logger.info(f"Loaded {len(db_chats)} required chats from database")
    yield

web_app = FastAPI(title="Konkurs Bot Web Admin", lifespan=lifespan)
templates = Jinja2Templates(directory="web_templates")

# Dependency to get DB session for FastAPI
async def get_db():
    async with session_pool() as session:
        try:
            yield session
        finally:
            await session.close()

# --- Web Routes ---
@web_app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db=Depends(get_db)):
    from app.services.user_service import get_users_count
    from app.services.contest_service import get_active_contests, get_all_contests, get_participants_count, get_winners
    from app.services.settings_service import get_required_chats

    users_count = await get_users_count(db)
    active_contests = await get_active_contests(db)
    all_contests = await get_all_contests(db)
    required_chats = await get_required_chats(db)
    
    total_participants = 0
    total_winners = 0
    for contest in all_contests:
        total_participants += await get_participants_count(db, contest.id)
        winners = await get_winners(db, contest.id)
        total_winners += len(winners)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "users_count": users_count,
        "active_contests_count": len(active_contests),
        "total_contests_count": len(all_contests),
        "total_participants": total_participants,
        "total_winners": total_winners,
        "required_chats_count": len(required_chats),
        "active_contests": active_contests[:5],
        "required_chats": required_chats
    })

@web_app.get("/contests", response_class=HTMLResponse)
async def list_contests(request: Request, db=Depends(get_db)):
    from app.services.contest_service import get_all_contests
    contests = await get_all_contests(db)
    return templates.TemplateResponse("contests.html", {
        "request": request,
        "contests": contests
    })

@web_app.get("/contest/{contest_id}", response_class=HTMLResponse)
async def contest_detail(request: Request, contest_id: int, db=Depends(get_db)):
    from app.services.contest_service import get_contest_by_id, get_participants, get_winners
    contest = await get_contest_by_id(db, contest_id)
    if not contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    
    participants = await get_participants(db, contest_id)
    winners = await get_winners(db, contest_id)
    
    return templates.TemplateResponse("contest_detail.html", {
        "request": request,
        "contest": contest,
        "participants": participants,
        "winners": winners
    })

@web_app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db=Depends(get_db)):
    from app.services.settings_service import get_required_chats
    required_chats = await get_required_chats(db)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "required_chats": required_chats
    })

@web_app.post("/settings/update")
async def update_settings(request: Request, db=Depends(get_db)):
    from app.services.settings_service import set_required_chats
    form_data = await request.form()
    chats_json = form_data.get("chats", "[]")
    try:
        import json
        chats = json.loads(chats_json)
        await set_required_chats(db, chats)
        # Update global config as well
        config.required_chats = chats
        return RedirectResponse(url="/settings?success=1", status_code=303)
    except Exception as e:
        logger.error(f"Settings update error: {e}")
        return RedirectResponse(url="/settings?error=1", status_code=303)

# --- Bot Initialization ---
bot = Bot(
    token=config.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=MemoryStorage())
dp.update.middleware(DbSessionMiddleware(session_pool=session_pool))
dp["config"] = config
dp.include_routers(start.router, admin.router, user.router, events.router)

async def run_bot():
    logger.info("Telegram bot ishga tushdi!")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

async def run_web():
    logger.info("Web admin panel ishga tushdi!")
    port = int(os.getenv("PORT", 8000))
    server_config = uvicorn.Config(web_app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(server_config)
    await server.serve()

async def main():
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
