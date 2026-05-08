from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.db.models import Base, Contest, Participant, Winner, Settings
from app.services.settings_service import get_required_chats, set_required_chats
from app.services.contest_service import (
    get_active_contests, get_all_contests, get_contest_by_id,
    get_participants_count, get_participants, get_winners
)
from app.services.user_service import get_users_count

load_dotenv()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/konkurs.db")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Create tables
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="Konkurs Bot Web Admin", lifespan=lifespan)

# Templates
templates = Jinja2Templates(directory="web_templates")

# Dependency to get DB session
async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

# Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    # Get statistics
    users_count = await get_users_count(db)
    active_contests = await get_active_contests(db)
    all_contests = await get_all_contests(db)
    required_chats = await get_required_chats(db)
    
    # Count participants and winners
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
        "active_contests": active_contests[:5],  # Show last 5 active
        "required_chats": required_chats
    })

@app.get("/contests", response_class=HTMLResponse)
async def list_contests(request: Request, db: AsyncSession = Depends(get_db)):
    contests = await get_all_contests(db)
    return templates.TemplateResponse("contests.html", {
        "request": request,
        "contests": contests
    })

@app.get("/contest/{contest_id}", response_class=HTMLResponse)
async def contest_detail(request: Request, contest_id: int, db: AsyncSession = Depends(get_db)):
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

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: AsyncSession = Depends(get_db)):
    required_chats = await get_required_chats(db)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "required_chats": required_chats
    })

@app.post("/settings/update")
async def update_settings(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    form_data = await request.form()
    chats_json = form_data.get("chats", "[]")
    try:
        import json
        chats = json.loads(chats_json)
        await set_required_chats(db, chats)
        return RedirectResponse(url="/settings?success=1", status_code=303)
    except Exception as e:
        return RedirectResponse(url="/settings?error=1", status_code=303)

# API endpoints
@app.get("/api/stats")
async def api_stats(db: AsyncSession = Depends(get_db)):
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
    
    return {
        "users_count": users_count,
        "active_contests": len(active_contests),
        "total_contests": len(all_contests),
        "total_participants": total_participants,
        "total_winners": total_winners,
        "required_chats": len(required_chats),
        "required_chats_list": required_chats
    }

@app.get("/api/contests")
async def api_contests(db: AsyncSession = Depends(get_db)):
    contests = await get_all_contests(db)
    return [{
        "id": c.id,
        "title": c.title,
        "description": c.description,
        "prize": c.prize,
        "winners_count": c.winners_count,
        "is_active": c.is_active,
        "require_subscription": c.require_subscription,
        "participants_count": 0,  # Will be filled below
        "created_at": c.created_at.isoformat() if c.created_at else None
    } for c in contests]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)