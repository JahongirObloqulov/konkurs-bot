import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
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


@router.get("/health")
async def health_check():
    return {"status": "ok"}


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
        from sqlalchemy.orm import selectinload
        
        # Get active contests with participant counts
        res = await session.execute(
            select(Contest)
            .order_by(Contest.created_at.desc())
            .limit(5)
        )
        recent_contests = res.scalars().all()
        
        # Fetch counts for each contest for display
        contests_data = []
        for c in recent_contests:
            p_count = await session.execute(select(func.count(Participant.id)).where(Participant.contest_id == c.id))
            contests_data.append({
                "id": c.id,
                "title": c.title,
                "prize": c.prize,
                "participants_count": p_count.scalar() or 0,
                "created_at": c.created_at,
                "is_active": c.is_active
            })

        active_contests_count_res = await session.execute(select(func.count(Contest.id)).where(Contest.is_active == True))
        active_contests_count = active_contests_count_res.scalar() or 0
        
        users_count = await get_users_count(session)
        
        total_participants = await session.execute(select(func.count(Participant.id)))
        total_participants = total_participants.scalar_one() or 0
        
        total_winners = await session.execute(select(func.count(Winner.id)))
        total_winners = total_winners.scalar_one() or 0
        
        total_referrals = await session.execute(select(func.sum(User.referral_count)))
        total_referrals = total_referrals.scalar() or 0
        
        total_additions = await session.execute(select(func.sum(User.added_users_count)))
        total_additions = total_additions.scalar() or 0
        
        # Growth calculation (today vs yesterday)
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        
        today_users = await session.execute(
            select(func.count(User.id)).where(func.date(User.registered_at) == today)
        )
        today_users_count = today_users.scalar_one() or 0
        
        yesterday_users = await session.execute(
            select(func.count(User.id)).where(func.date(User.registered_at) == yesterday)
        )
        yesterday_users_count = yesterday_users.scalar_one() or 0
        
        growth_pct = 0
        if yesterday_users_count > 0:
            growth_pct = ((today_users_count - yesterday_users_count) / yesterday_users_count) * 100
        elif today_users_count > 0:
            growth_pct = 100

        recent_participants = await session.execute(
            select(Participant).order_by(Participant.joined_at.desc()).limit(10)
        )
        recent_participants = recent_participants.scalars().all()

    return templates.TemplateResponse(
        "pages/dashboard.html",
        {
            "request": request,
            "user": user,
            "active_contests_count": active_contests_count,
            "contests": contests_data,
            "total_users": users_count,
            "total_participants": total_participants,
            "total_winners": total_winners,
            "total_referrals": total_referrals,
            "total_additions": total_additions,
            "recent_participants": recent_participants,
            "growth_pct": growth_pct,
        }
    )


@router.get("/export/dashboard/{format}")
async def export_dashboard(format: str, user: dict = Depends(require_auth)):
    from app.db.models import User
    from app.services.export_service import generate_excel, generate_pdf
    
    async with async_session_maker() as session:
        users_res = await session.execute(select(User))
        users = users_res.scalars().all()
        
        data = []
        for u in users:
            data.append({
                "User ID": u.user_id,
                "Username": u.username or "N/A",
                "Full Name": u.full_name or "N/A",
                "Referrals": u.referral_count,
                "Joined At": u.registered_at.strftime('%Y-%m-%d %H:%M') if u.registered_at else "N/A"
            })
            
        from app.services.audit_service import log_action
        await log_action(session, user['sub'], "Export Dashboard", f"Format: {format}")

        if format == "excel":
            content, filename = await generate_excel(data, "users_report")
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            content, filename = await generate_pdf(data, "Users Report")
            return Response(
                content=content,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )


@router.get("/audit-logs", response_class=HTMLResponse)
async def audit_logs_page(request: Request, user: dict = Depends(require_auth)):
    from app.db.models import AuditLog
    async with async_session_maker() as session:
        res = await session.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)
        )
        logs = res.scalars().all()
        
    return templates.TemplateResponse(
        "pages/audit_logs.html",
        {"request": request, "user": user, "logs": logs}
    )


@router.get("/api/stats/growth")
async def api_stats_growth(user: dict = Depends(require_auth)):
    from app.db.models import User
    from datetime import datetime, timedelta, timezone
    
    async with async_session_maker() as session:
        today = datetime.now(timezone.utc).date()
        dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
        
        labels = [d.strftime('%b %d') for d in dates]
        values = []
        
        for d in dates:
            res = await session.execute(
                select(func.count(User.id)).where(
                    func.date(User.registered_at) == d
                )
            )
            values.append(res.scalar_one() or 0)
            
    return JSONResponse({
        "labels": labels,
        "values": values
    })


@router.post("/api/contests/{contest_id}/pick-winners")
async def api_pick_winners(contest_id: int, user: dict = Depends(require_auth)):
    from app.services.contest_service import select_winners
    from app.services.audit_service import log_action
    
    async with async_session_maker() as session:
        winners = await select_winners(session, contest_id)
        if not winners:
            return JSONResponse({"status": "error", "message": "Winners already selected or contest not found"}, status_code=400)
            
        await log_action(session, user['sub'], "Pick Winners", f"Contest ID: {contest_id}, {len(winners)} winners selected.")
        
        return JSONResponse({
            "status": "success",
            "winners": [{"name": w.full_name, "id": w.user_id} for w in winners]
        })


@router.get("/export/contest/{contest_id}/{format}")
async def export_contest_participants(contest_id: int, format: str, user: dict = Depends(require_auth)):
    from app.db.models import Participant, Contest
    from app.services.export_service import generate_excel, generate_pdf
    
    async with async_session_maker() as session:
        contest = await session.get(Contest, contest_id)
        if not contest:
            raise HTTPException(status_code=404, detail="Contest not found")
            
        res = await session.execute(
            select(Participant).where(Participant.contest_id == contest_id).order_by(Participant.joined_at.desc())
        )
        participants = res.scalars().all()
        
        data = []
        for p in participants:
            data.append({
                "Telegram ID": p.telegram_id,
                "Full Name": p.full_name,
                "Referrals": p.referral_count,
                "Joined At": p.joined_at.strftime('%Y-%m-%d %H:%M') if p.joined_at else ""
            })
            
        prefix = f"contest_{contest_id}_participants"
        from app.services.audit_service import log_action
        await log_action(session, user['sub'], "Export Contest", f"Contest ID: {contest_id}, Format: {format}")

        title = f"Contest Participants: {contest.title}"
        
        if format == "excel":
            content, filename = await generate_excel(data, prefix)
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            content, filename = await generate_pdf(data, title)
            return Response(
                content=content,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )


@router.get("/contests/new", response_class=HTMLResponse)
async def contest_new(request: Request, user: dict = Depends(require_auth)):
    from app.db.models import Media
    async with async_session_maker() as session:
        res = await session.execute(select(Media).order_by(Media.created_at.desc()))
        media_gallery = res.scalars().all()
        
    return templates.TemplateResponse(
        "pages/contest_form.html",
        {"request": request, "user": user, "contest": None, "media_gallery": media_gallery}
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
            media_type=form.get("media_type") or None,
            file_id=form.get("file_id") or None,
            min_referrals=int(form.get("min_referrals", 0)),
            min_additions=int(form.get("min_additions", 0)),
        )
        if not contest:
            return templates.TemplateResponse(
                "pages/contest_form.html",
                {"request": request, "user": user, "contest": None, "error": "Xatolik yuz berdi!"}
            )
        from app.services.audit_service import log_action
        await log_action(session, user['sub'], "Create Contest", f"Title: {form.get('title')}, Prize: {form.get('prize')}")

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
        
        from app.db.models import User
        query = (
            select(Participant, User.referral_count, User.added_users_count)
            .join(User, User.user_id == Participant.user_id)
            .where(Participant.contest_id == contest_id)
            .order_by(Participant.joined_at.desc())
        )
        result = await session.execute(query)
        rows = result.all()
        
        # Format for template: list of dicts or objects with combined attributes
        participants = []
        for p, ref_count, add_count in rows:
            participants.append({
                "user_id": p.user_id,
                "user_name": p.full_name,
                "referral_count": ref_count,
                "addition_count": add_count,
                "joined_at": p.joined_at
            })
        
        winners = await get_winners(session, contest_id)
        participants_count = len(participants)

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
        from app.services.audit_service import log_action
        await log_action(session, user['sub'], "Delete Contest", f"Contest ID: {contest_id}")

    return RedirectResponse(url="/contests", status_code=302)


@router.post("/contests/{contest_id}/pick-winners")
async def contest_pick_winners(request: Request, contest_id: int, user: dict = Depends(require_auth)):
    from app.services.contest_service import select_winners, get_contest_by_id, get_winners, get_participants
    from app.utils.formatting import format_results_view
    import asyncio
    bot = request.app.state.bot

    async with async_session_maker() as session:
        winners = await select_winners(session, contest_id)
        contest = await get_contest_by_id(session, contest_id)
        participants = await get_participants(session, contest_id)

    if winners and contest:
        text = format_results_view(contest, winners) + "\n\n\U0001f389 Tabriklaymiz!"
        
        # Background notification
        async def notify_participants():
            for p in participants:
                try:
                    await bot.send_message(p.user_id, text, parse_mode="HTML")
                    await asyncio.sleep(0.05)
                except Exception:
                    pass
        
        asyncio.create_task(notify_participants())

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


@router.get("/audit-logs", response_class=HTMLResponse)
async def audit_logs_page(request: Request, user: dict = Depends(require_auth)):
    from app.db.models import AuditLog
    async with async_session_maker() as session:
        res = await session.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100))
        logs = res.scalars().all()
        
    return templates.TemplateResponse(
        "pages/audit_logs.html",
        {"request": request, "user": user, "logs": logs}
    )


@router.get("/media-gallery", response_class=HTMLResponse)
async def media_gallery_page(request: Request, user: dict = Depends(require_auth)):
    from app.db.models import Media
    async with async_session_maker() as session:
        res = await session.execute(select(Media).order_by(Media.created_at.desc()))
        media_items = res.scalars().all()
        
    return templates.TemplateResponse(
        "pages/media_gallery.html",
        {"request": request, "user": user, "media_items": media_items}
    )


@router.post("/api/media/add")
async def api_media_add(request: Request, user: dict = Depends(require_auth)):
    from app.db.models import Media
    from app.services.audit_service import log_action
    
    form = await request.form()
    file_id = form.get("file_id")
    file_type = form.get("file_type")
    description = form.get("description")
    
    if not file_id or not file_type:
        return JSONResponse({"status": "error", "message": "Missing fields"}, status_code=400)
        
    async with async_session_maker() as session:
        media = Media(file_id=file_id, file_type=file_type, description=description)
        session.add(media)
        await session.commit()
        await log_action(session, user['sub'], "Add Media", f"File ID: {file_id}, Type: {file_type}")
        
    return RedirectResponse(url="/media-gallery", status_code=302)


import asyncio
from typing import List

sse_queues: List[asyncio.Queue] = []

@router.get("/api/sse")
async def sse_endpoint(request: Request):
    queue = asyncio.Queue()
    sse_queues.append(queue)
    
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    # Wait with timeout to occasionally check for disconnect
                    data = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            if queue in sse_queues:
                sse_queues.remove(queue)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

async def notify_sse(message: str):
    for queue in sse_queues:
        await queue.put(message)


@router.post("/api/ai/draft")
async def api_ai_draft(request: Request, user: dict = Depends(require_auth)):
    import httpx
    import os
    
    try:
        data = await request.json()
        prompt = data.get("prompt")
        lang = data.get("lang", "uz")
        
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL", "google/gemini-flash-1.5-exp:free")
        
        if not api_key:
            return JSONResponse({"status": "error", "message": "AI API key not configured (OPENROUTER_API_KEY)"}, status_code=500)
            
        system_instruction = f"You are a helpful telegram bot administrator. Draft a short, engaging broadcast message in {lang}. Use HTML tags like <b>, <i> if needed. Keep it concise."
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Topic: {prompt}"}
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            # Fallback if rate limited (429), not found (404), or provider error
            if response.status_code in [404, 429] or "rate-limited" in response.text or "No endpoints found" in response.text:
                fallback_model = "openrouter/free"
                if model != fallback_model:
                    payload["model"] = fallback_model
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=30.0
                    )
            
        if response.status_code != 200:
            return JSONResponse({
                "status": "error", 
                "message": f"OpenRouter Error ({response.status_code}): {response.text}",
                "tip": "Model nomini tekshiring yoki OpenRouter-da limit tugagan bo'lishi mumkin."
            }, status_code=response.status_code)
            
        res_data = response.json()
        if 'choices' not in res_data or not res_data['choices']:
            return JSONResponse({"status": "error", "message": f"AI Response empty: {res_data}"}, status_code=500)
            
        draft = res_data['choices'][0]['message']['content']
        
        return JSONResponse({
            "status": "success",
            "draft": draft.strip()
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: dict = Depends(require_auth)):
    from app.services.settings_service import get_setting
    async with async_session_maker() as session:
        reg_welcome = await get_setting(session, "registration_welcome", "Xush kelibsiz! Ro'yxatdan o'tishni boshlaymiz.\n\nIsmingizni kiriting:")
        reg_success = await get_setting(session, "registration_success", "✅ Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!")
        sub_required = await get_setting(session, "subscription_required", "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling!</b>\n\nBarcha kanallarga obuna bo'lgach, \"Obunani tekshirish\" tugmasini bosing.")
        sub_success = await get_setting(session, "subscription_success", "✅ Tabriklaymiz! Obuna tasdiqlandi. Endi botdan to'liq foydalanishingiz mumkin.")
        sub_success_media_id = await get_setting(session, "sub_success_media_id", "")
        sub_success_media_type = await get_setting(session, "sub_success_media_type", "")

    return templates.TemplateResponse(
        "pages/settings.html",
        {
            "request": request,
            "user": user,
            "reg_welcome": reg_welcome,
            "reg_success": reg_success,
            "sub_required": sub_required,
            "sub_success": sub_success,
            "sub_success_media_id": sub_success_media_id,
            "sub_success_media_type": sub_success_media_type,
        }
    )


@router.post("/settings")
async def update_settings(request: Request, user: dict = Depends(require_auth)):
    from app.services.settings_service import set_setting
    form = await request.form()
    
    async with async_session_maker() as session:
        await set_setting(session, "registration_welcome", form.get("reg_welcome"))
        await set_setting(session, "registration_success", form.get("reg_success"))
        await set_setting(session, "subscription_required", form.get("sub_required"))
        await set_setting(session, "subscription_success", form.get("sub_success"))
        await set_setting(session, "sub_success_media_id", form.get("sub_success_media_id"))
        await set_setting(session, "sub_success_media_type", form.get("sub_success_media_type"))
    
    return RedirectResponse(url="/settings?success=1", status_code=302)


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

@router.get("/broadcast", response_class=HTMLResponse)
async def broadcast_page(request: Request, user: dict = Depends(require_auth)):
    from app.db.models import BroadcastLog, Media
    success = request.query_params.get("success")
    error = request.query_params.get("error")
    
    async with async_session_maker() as session:
        # Get broadcast logs
        res = await session.execute(
            select(BroadcastLog).order_by(BroadcastLog.created_at.desc()).limit(10)
        )
        logs = res.scalars().all()
        
        # Get media items for selection
        media_res = await session.execute(select(Media).order_by(Media.created_at.desc()))
        media_gallery = media_res.scalars().all()
        
    return templates.TemplateResponse(
        "pages/broadcast.html",
        {
            "request": request, 
            "user": user, 
            "success": success, 
            "error": error, 
            "logs": logs,
            "media_gallery": media_gallery
        }
    )


@router.post("/broadcast")
async def broadcast_send(request: Request, user: dict = Depends(require_auth)):
    from app.db.models import User, BroadcastLog, AuditLog
    bot = request.app.state.bot
    import asyncio
    import json
    
    form = await request.form()
    message_uz = form.get("message_uz")
    message_ru = form.get("message_ru") or message_uz
    message_en = form.get("message_en") or message_uz
    
    media_types = form.getlist("media_type")
    file_ids_raw = form.getlist("file_id")
    
    media_items = []
    for mtype, fid_raw in zip(media_types, file_ids_raw):
        if not mtype: continue
        for fid in fid_raw.split(","):
            if fid.strip():
                media_items.append({"type": mtype, "id": fid.strip()})
    
    messages = {
        "uz": message_uz,
        "ru": message_ru,
        "en": message_en
    }
    
    async with async_session_maker() as session:
        # Get all users with their language
        res = await session.execute(select(User.user_id, User.language_code))
        users_data = res.all() # list of tuples (user_id, language_code)
        
        if not users_data:
            return RedirectResponse(url="/broadcast?error=Foydalanuvchilar topilmadi", status_code=302)

        # Save to BroadcastLog (storing as JSON for history)
        blog_msg = json.dumps(messages)
        blog = BroadcastLog(
            admin_username=user['sub'],
            message=blog_msg,
            media_data=json.dumps(media_items),
        )
        session.add(blog)
        
        # Log in AuditLog
        audit = AuditLog(
            admin_username=user['sub'],
            action="Broadcast",
            details=f"Users: {len(users_data)}, Multi-lang: {', '.join(messages.keys())}"
        )
        session.add(audit)
        await session.commit()

    # Background task for sending
    async def send_broadcast():
        from aiogram.utils.media_group import MediaGroupBuilder
        from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
        
        success_count = 0
        fail_count = 0
        
        for user_id, lang_code in users_data:
            try:
                lang = lang_code or "uz"
                text = messages.get(lang, message_uz)
                
                if not media_items:
                    await bot.send_message(user_id, text, parse_mode="HTML")
                elif len(media_items) == 1:
                    m = media_items[0]
                    if m['type'] == 'photo':
                        await bot.send_photo(user_id, m['id'], caption=text, parse_mode="HTML")
                    else:
                        await bot.send_video(user_id, m['id'], caption=text, parse_mode="HTML")
                else:
                    # Media group (max 10)
                    album_builder = MediaGroupBuilder(caption=text)
                    for m in media_items[:10]:
                        if m['type'] == 'photo':
                            album_builder.add_photo(media=m['id'])
                        else:
                            album_builder.add_video(media=m['id'])
                    await bot.send_media_group(user_id, media=album_builder.build())
                
                success_count += 1
                await asyncio.sleep(0.05) # Rate limiting
            except TelegramForbiddenError:
                fail_count += 1
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except Exception:
                fail_count += 1
        
        print(f"Broadcast finished: {success_count} success, {fail_count} failed")

    asyncio.create_task(send_broadcast())
    
    return RedirectResponse(url=f"/broadcast?success={len(users_data)} ta foydalanuvchiga yuborish boshlandi", status_code=302)

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