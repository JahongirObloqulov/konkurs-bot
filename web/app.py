import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

from app.config import Config
from app.db.engine import create_engine, init_db, create_session_pool

config = Config.from_env()

engine = create_engine(config.db_url)
async_session_maker = create_session_pool(engine)

from web.translations import translate

import json
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Register filters
templates.env.filters["from_json"] = json.loads
templates.env.filters["datetime"] = lambda dt: dt.strftime('%Y-%m-%d %H:%M') if dt else ""

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

app = FastAPI(
    title="Konkurs Bot Admin",
    description="Telegram bot uchun web admin panel",
    version="1.0.0",
    lifespan=lifespan,
)

@app.middleware("http")
async def add_translation_helper(request: Request, call_next):
    lang = request.cookies.get("lang", "uz")
    if lang not in ["uz", "ru", "en"]:
        lang = "uz"
    
    # Add translation function to request state
    request.state.lang = lang
    
    # Define the translation function for this request
    def _(key):
        return translate(key, lang)
    
    # Add to template context
    templates.env.globals["_"] = _
    templates.env.globals["current_lang"] = lang
    
    response = await call_next(request)
    return response

@app.get("/health")
async def health_check():
    return {"status": "ok"}

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

from web import routes, crm_routes

app.include_router(routes.router)
app.include_router(crm_routes.router)