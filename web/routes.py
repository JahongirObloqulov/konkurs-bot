import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, func

from web.app import templates, async_session_maker

load_dotenv()

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("WEB_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ADMIN_USERNAME = os.getenv("WEB_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = pwd_context.hash(os.getenv("WEB_ADMIN_PASSWORD", "admin123"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def require_auth(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    error = request.query_params.get("error")
    return templates.TemplateResponse(
        "pages/login.html",
        {"request": request, "error": error}
    )


@router.post("/login")
async def login(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    
    if username == ADMIN_USERNAME and verify_password(password, ADMIN_PASSWORD_HASH):
        token = create_access_token({"sub": username})
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")
        return response
    
    return templates.TemplateResponse(
        "pages/login.html",
        {"request": request, "error": "Noto'g'ri username yoki password!"},
        status_code=401,
    )


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: dict = Depends(require_auth)):
    from app.db.models import Contest, Participant, Winner, User
    from app.services.contest_service import get_active_contests
    from app.services.user_service import get_users_count

    async with async_session_maker() as session:
        active_contests = await get_active_contests(session)
        all_contests = await session.execute(select(Contest))
        all_contests = all_contests.scalars().all()
        
        users_count = await get_users_count(session)
        
        total_participants = await session.execute(select(func.count(Participant.id)))
        total_participants = total_participants.scalar_one() or 0
        
        total_winners = await session.execute(select(func.count(Winner.id)))
        total_winners = total_winners.scalar_one() or 0
        
        recent_participants = await session.execute(
            select(Participant).order_by(Participant.joined_at.desc()).limit(10)
        )
        recent_participants = recent_participants.scalars().all()

    return templates.TemplateResponse(
        "pages/dashboard.html",
        {
            "request": request,
            "user": user,
            "active_contests": len(active_contests),
            "total_contests": len(all_contests),
            "total_users": users_count,
            "total_participants": total_participants,
            "total_winners": total_winners,
            "recent_participants": recent_participants,
        }
    )


@router.get("/contests/new", response_class=HTMLResponse)
async def contest_new(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse(
        "pages/contest_form.html",
        {"request": request, "user": user, "contest": None}
    )


@router.post("/contests/new")
async def contest_create(request: Request, user: dict = Depends(require_auth)):
    from app.services.contest_service import create_contest

    form = await request.form()
    async with async_session_maker() as session:
        contest = await create_contest(
            session,
            title=form.get("title"),
            description=form.get("description"),
            prize=form.get("prize"),
            winners_count=int(form.get("winners_count", 1)),
            require_subscription=form.get("require_subscription") == "on",
            created_by=0,
        )
        if not contest:
            return templates.TemplateResponse(
                "pages/contest_form.html",
                {"request": request, "user": user, "contest": None, "error": "Xatolik yuz berdi!"}
            )
    return RedirectResponse(url=f"/contests/{contest.id}", status_code=302)


@router.get("/contests", response_class=HTMLResponse)
async def contests_page(request: Request, user: dict = Depends(require_auth)):
    from app.db.models import Contest
    from app.services.contest_service import get_all_contests

    async with async_session_maker() as session:
        contests = await get_all_contests(session)

    return templates.TemplateResponse(
        "pages/contests.html",
        {"request": request, "user": user, "contests": contests}
    )


@router.get("/contests/{contest_id}", response_class=HTMLResponse)
async def contest_detail(request: Request, contest_id: int, user: dict = Depends(require_auth)):
    from app.db.models import Participant, Winner
    from app.services.contest_service import get_contest_by_id, get_participants, get_winners, get_participants_count

    async with async_session_maker() as session:
        contest = await get_contest_by_id(session, contest_id)
        if not contest:
            raise HTTPException(status_code=404, detail="Contest not found")
        
        participants = await get_participants(session, contest_id)
        winners = await get_winners(session, contest_id)
        participants_count = await get_participants_count(session, contest_id)

    return templates.TemplateResponse(
        "pages/contest_detail.html",
        {
            "request": request,
            "user": user,
            "contest": contest,
            "participants": participants,
            "winners": winners,
            "participants_count": participants_count,
        }
    )


@router.post("/contests/{contest_id}/end")
async def contest_end(request: Request, contest_id: int, user: dict = Depends(require_auth)):
    from app.services.contest_service import end_contest

    async with async_session_maker() as session:
        await end_contest(session, contest_id)
    return RedirectResponse(url=f"/contests/{contest_id}", status_code=302)


@router.post("/contests/{contest_id}/delete")
async def contest_delete(request: Request, contest_id: int, user: dict = Depends(require_auth)):
    from app.services.contest_service import delete_contest

    async with async_session_maker() as session:
        await delete_contest(session, contest_id)
    return RedirectResponse(url="/contests", status_code=302)


@router.post("/contests/{contest_id}/pick-winners")
async def contest_pick_winners(request: Request, contest_id: int, user: dict = Depends(require_auth)):
    from app.services.contest_service import select_winners

    async with async_session_maker() as session:
        await select_winners(session, contest_id)
    return RedirectResponse(url=f"/contests/{contest_id}", status_code=302)


@router.get("/chats", response_class=HTMLResponse)
async def chats_page(request: Request, user: dict = Depends(require_auth)):
    from app.services.settings_service import get_required_chats

    async with async_session_maker() as session:
        chats = await get_required_chats(session)

    return templates.TemplateResponse(
        "pages/chats.html",
        {"request": request, "user": user, "chats": chats}
    )


@router.post("/chats/add")
async def chat_add(request: Request, user: dict = Depends(require_auth)):
    from app.services.settings_service import get_required_chats, set_required_chats

    form = await request.form()
    new_chat = {
        "id": int(form.get("chat_id")),
        "username": form.get("username", "").strip("@"),
        "type": form.get("type", "channel"),
    }

    async with async_session_maker() as session:
        chats = await get_required_chats(session)
        chats.append(new_chat)
        await set_required_chats(session, chats)

    return RedirectResponse(url="/chats", status_code=302)


@router.post("/chats/{chat_id}/remove")
async def chat_remove(request: Request, chat_id: int, user: dict = Depends(require_auth)):
    from app.services.settings_service import get_required_chats, set_required_chats

    async with async_session_maker() as session:
        chats = await get_required_chats(session)
        chats = [c for c in chats if c["id"] != chat_id]
        await set_required_chats(session, chats)

    return RedirectResponse(url="/chats", status_code=302)


@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, user: dict = Depends(require_auth)):
    from app.db.models import User

    async with async_session_maker() as session:
        result = await session.execute(select(User).order_by(User.registered_at.desc()).limit(100))
        users = result.scalars().all()

    return templates.TemplateResponse(
        "pages/users.html",
        {"request": request, "user": user, "users": users}
    )


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail(request: Request, user_id: int, user: dict = Depends(require_auth)):
    from app.db.models import User, Participant

    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        participations = await session.execute(
            select(Participant).where(Participant.user_id == user_id)
        )
        participations = participations.scalars().all()

    return templates.TemplateResponse(
        "pages/user_detail.html",
        {
            "request": request,
            "user": user,
            "db_user": db_user,
            "participations": participations,
        }
    )


@router.get("/api/stats")
async def api_stats(user: dict = Depends(require_auth)):
    from app.db.models import Contest, Participant, Winner, User
    from app.services.contest_service import get_active_contests
    from app.services.user_service import get_users_count

    async with async_session_maker() as session:
        active_contests = await get_active_contests(session)
        all_contests = await session.execute(select(Contest))
        all_contests = all_contests.scalars().all()
        users_count = await get_users_count(session)
        
        total_participants = await session.execute(select(func.count(Participant.id)))
        total_participants = total_participants.scalar_one() or 0
        
        total_winners = await session.execute(select(func.count(Winner.id)))
        total_winners = total_winners.scalar_one() or 0

    return JSONResponse({
        "total_users": users_count,
        "total_contests": len(all_contests),
        "active_contests": len(active_contests),
        "total_participants": total_participants,
        "total_winners": total_winners,
    })


@router.get("/api/contests")
async def api_contests(user: dict = Depends(require_auth)):
    from app.services.contest_service import get_all_contests

    async with async_session_maker() as session:
        contests = await get_all_contests(session)
        return JSONResponse([
            {
                "id": c.id,
                "title": c.title,
                "is_active": c.is_active,
                "winners_count": c.winners_count,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in contests
        ])