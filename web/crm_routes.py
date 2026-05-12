from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select

from app.services.crm_service import (
    add_tag_to_customer,
    create_business,
    create_customer,
    create_interaction,
    create_tag,
    delete_business,
    delete_customer,
    get_all_businesses,
    get_all_tags,
    get_business_by_id,
    get_businesses_count,
    get_customer_by_id,
    get_customers_by_business,
    get_customers_count,
    get_interactions_by_customer,
    remove_tag_from_customer,
    update_business,
    update_customer,
)
from app.db.models import Customer, CustomerTag
from web.app import templates, async_session_maker
from web.routes import require_auth, get_current_user

router = APIRouter()


@router.get("/crm", response_class=HTMLResponse)
async def crm_dashboard(request: Request, user: dict = Depends(require_auth)):
    async with async_session_maker() as session:
        from app.db.models import AuditLog
        
        businesses = await get_all_businesses(session)
        customers_count = await get_customers_count(session)
        businesses_count = await get_businesses_count(session)
        tags = await get_all_tags(session)
        
        # Real activity from AuditLog
        res = await session.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(5)
        )
        recent_activity = res.scalars().all()

    return templates.TemplateResponse(
        "pages/crm/dashboard.html",
        {
            "request": request,
            "user": user,
            "businesses": businesses,
            "customers_count": customers_count,
            "businesses_count": businesses_count,
            "tags_count": len(tags),
            "recent_activity": recent_activity
        }
    )


@router.get("/export/crm/{format}")
async def export_crm(format: str, user: dict = Depends(require_auth)):
    from app.services.crm_service import get_all_businesses, get_all_customers
    from app.services.export_service import generate_excel, generate_pdf
    from app.db.models import Customer
    from sqlalchemy.orm import selectinload
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(Customer).options(selectinload(Customer.business))
        )
        customers = result.scalars().all()
        
        data = []
        for c in customers:
            data.append({
                "ID": c.id,
                "Full Name": c.full_name,
                "Business": c.business.name if c.business else "None",
                "Phone": c.phone,
                "Email": c.email,
                "Joined At": c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else ""
            })
            
        from app.services.audit_service import log_action
        await log_action(session, user['sub'], "Export CRM", f"Format: {format}")

        if format == "excel":
            content, filename = await generate_excel(data, "crm_customers_report")
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            content, filename = await generate_pdf(data, "CRM Customers Report")
            return Response(
                content=content,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )


@router.get("/export/business/{business_id}/{format}")
async def export_business_customers(business_id: int, format: str, user: dict = Depends(require_auth)):
    from app.db.models import Customer, Business
    from app.services.export_service import generate_excel, generate_pdf
    
    async with async_session_maker() as session:
        business = await session.get(Business, business_id)
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
            
        res = await session.execute(
            select(Customer).where(Customer.business_id == business_id).order_by(Customer.created_at.desc())
        )
        customers = res.scalars().all()
        
        data = []
        for c in customers:
            data.append({
                "Full Name": c.full_name,
                "Phone": c.phone,
                "Email": c.email,
                "Joined At": c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else ""
            })
            
        prefix = f"business_{business_id}_customers"
        title = f"Business Customers: {business.name}"
        
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


@router.get("/crm/businesses", response_class=HTMLResponse)
async def crm_businesses(request: Request, user: dict = Depends(require_auth)):
    async with async_session_maker() as session:
        businesses = await get_all_businesses(session)
    
    return templates.TemplateResponse(
        "pages/crm/businesses.html",
        {"request": request, "user": user, "businesses": businesses}
    )


@router.get("/crm/businesses/new", response_class=HTMLResponse)
async def crm_business_new(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse(
        "pages/crm/business_form.html",
        {"request": request, "user": user, "business": None}
    )


@router.post("/crm/businesses/new")
async def crm_business_create(request: Request, user: dict = Depends(require_auth)):
    form = await request.form()
    async with async_session_maker() as session:
        await create_business(
            session,
            name=form.get("name"),
            phone=form.get("phone"),
            email=form.get("email"),
            address=form.get("address"),
            description=form.get("description"),
            created_by=user.get("user_id", 0),
        )
        from app.services.audit_service import log_action
        await log_action(session, user['sub'], "Create Business", f"Name: {form.get('name')}")
    return RedirectResponse(url="/crm/businesses", status_code=302)


@router.get("/crm/businesses/{business_id}", response_class=HTMLResponse)
async def crm_business_detail(request: Request, business_id: int, user: dict = Depends(require_auth)):
    async with async_session_maker() as session:
        business = await get_business_by_id(session, business_id)
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        customers = await get_customers_by_business(session, business_id)
    
    return templates.TemplateResponse(
        "pages/crm/business_detail.html",
        {
            "request": request,
            "user": user,
            "business": business,
            "customers": customers,
        }
    )


@router.get("/crm/businesses/{business_id}/edit", response_class=HTMLResponse)
async def crm_business_edit(request: Request, business_id: int, user: dict = Depends(require_auth)):
    async with async_session_maker() as session:
        business = await get_business_by_id(session, business_id)
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
    
    return templates.TemplateResponse(
        "pages/crm/business_form.html",
        {"request": request, "user": user, "business": business}
    )


@router.post("/crm/businesses/{business_id}/edit")
async def crm_business_update(request: Request, business_id: int, user: dict = Depends(require_auth)):
    form = await request.form()
    async with async_session_maker() as session:
        await update_business(
            session,
            business_id,
            name=form.get("name"),
            phone=form.get("phone"),
            email=form.get("email"),
            address=form.get("address"),
            description=form.get("description"),
        )
    return RedirectResponse(url=f"/crm/businesses/{business_id}", status_code=302)


@router.post("/crm/businesses/{business_id}/delete")
async def crm_business_delete(request: Request, business_id: int, user: dict = Depends(require_auth)):
    async with async_session_maker() as session:
        await delete_business(session, business_id)
        from app.services.audit_service import log_action
        await log_action(session, user['sub'], "Delete Business", f"ID: {business_id}")
    return RedirectResponse(url="/crm/businesses", status_code=302)


@router.get("/crm/customers", response_class=HTMLResponse)
async def crm_customers(request: Request, user: dict = Depends(require_auth)):
    from sqlalchemy.orm import selectinload
    async with async_session_maker() as session:
        result = await session.execute(
            select(Customer)
            .options(selectinload(Customer.business), selectinload(Customer.tags).selectinload(CustomerTag.tag))
            .order_by(Customer.created_at.desc())
            .limit(100)
        )
        customers = result.scalars().all()
    
    return templates.TemplateResponse(
        "pages/crm/customers.html",
        {"request": request, "user": user, "customers": customers}
    )


@router.get("/crm/customers/new", response_class=HTMLResponse)
async def crm_customer_new(request: Request, user: dict = Depends(require_auth)):
    async with async_session_maker() as session:
        businesses = await get_all_businesses(session)
        tags = await get_all_tags(session)
    
    return templates.TemplateResponse(
        "pages/crm/customer_form.html",
        {
            "request": request,
            "user": user,
            "customer": None,
            "businesses": businesses,
            "tags": tags,
            "customer_tags": [],
        }
    )


@router.post("/crm/customers/new")
async def crm_customer_create(request: Request, user: dict = Depends(require_auth)):
    form = await request.form()
    async with async_session_maker() as session:
        customer = await create_customer(
            session,
            business_id=int(form.get("business_id")),
            full_name=form.get("full_name"),
            phone=form.get("phone"),
            email=form.get("email"),
            notes=form.get("notes"),
            user_id=int(form.get("user_id")) if form.get("user_id") else None,
        )
        tag_ids = form.getlist("tag_ids")
        for tag_id in tag_ids:
            await add_tag_to_customer(session, customer.id, int(tag_id))
        
        from app.services.audit_service import log_action
        await log_action(session, user['sub'], "Create Customer", f"Name: {customer.full_name}")
    
    return RedirectResponse(url=f"/crm/customers/{customer.id}", status_code=302)


@router.get("/crm/customers/{customer_id}", response_class=HTMLResponse)
async def crm_customer_detail(request: Request, customer_id: int, user: dict = Depends(require_auth)):
    async with async_session_maker() as session:
        customer = await get_customer_by_id(session, customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        interactions = await get_interactions_by_customer(session, customer_id)
    
    return templates.TemplateResponse(
        "pages/crm/customer_detail.html",
        {
            "request": request,
            "user": user,
            "customer": customer,
            "interactions": interactions,
        }
    )


@router.get("/crm/customers/{customer_id}/edit", response_class=HTMLResponse)
async def crm_customer_edit(request: Request, customer_id: int, user: dict = Depends(require_auth)):
    async with async_session_maker() as session:
        customer = await get_customer_by_id(session, customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        businesses = await get_all_businesses(session)
        tags = await get_all_tags(session)
        customer_tags = [ct.tag_id for ct in customer.tags]
    
    return templates.TemplateResponse(
        "pages/crm/customer_form.html",
        {
            "request": request,
            "user": user,
            "customer": customer,
            "businesses": businesses,
            "tags": tags,
            "customer_tags": customer_tags,
        }
    )


@router.post("/crm/customers/{customer_id}/edit")
async def crm_customer_update(request: Request, customer_id: int, user: dict = Depends(require_auth)):
    form = await request.form()
    async with async_session_maker() as session:
        await update_customer(
            session,
            customer_id,
            full_name=form.get("full_name"),
            phone=form.get("phone"),
            email=form.get("email"),
            notes=form.get("notes"),
        )
        customer = await get_customer_by_id(session, customer_id)
        current_tags = [ct.tag_id for ct in customer.tags]
        new_tags = [int(t) for t in form.getlist("tag_ids")]
        
        for tag_id in current_tags:
            if tag_id not in new_tags:
                await remove_tag_from_customer(session, customer_id, tag_id)
        for tag_id in new_tags:
            if tag_id not in current_tags:
                await add_tag_to_customer(session, customer_id, tag_id)
    
    return RedirectResponse(url=f"/crm/customers/{customer_id}", status_code=302)


@router.post("/crm/customers/{customer_id}/delete")
async def crm_customer_delete(request: Request, customer_id: int, user: dict = Depends(require_auth)):
    async with async_session_maker() as session:
        await delete_customer(session, customer_id)
    return RedirectResponse(url="/crm/customers", status_code=302)


@router.get("/crm/customers/{customer_id}/interactions/new", response_class=HTMLResponse)
async def crm_interaction_new(request: Request, customer_id: int, user: dict = Depends(require_auth)):
    async with async_session_maker() as session:
        customer = await get_customer_by_id(session, customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
    
    return templates.TemplateResponse(
        "pages/crm/interaction_form.html",
        {"request": request, "user": user, "customer": customer}
    )


@router.post("/crm/customers/{customer_id}/interactions/new")
async def crm_interaction_create(request: Request, customer_id: int, user: dict = Depends(require_auth)):
    form = await request.form()
    async with async_session_maker() as session:
        await create_interaction(
            session,
            customer_id=customer_id,
            interaction_type=form.get("interaction_type"),
            description=form.get("description"),
            created_by=user.get("user_id", 0),
        )
    return RedirectResponse(url=f"/crm/customers/{customer_id}", status_code=302)


@router.get("/crm/tags", response_class=HTMLResponse)
async def crm_tags(request: Request, user: dict = Depends(require_auth)):
    async with async_session_maker() as session:
        tags = await get_all_tags(session)
    
    return templates.TemplateResponse(
        "pages/crm/tags.html",
        {"request": request, "user": user, "tags": tags}
    )


@router.post("/crm/tags/new")
async def crm_tag_create(request: Request, user: dict = Depends(require_auth)):
    form = await request.form()
    async with async_session_maker() as session:
        await create_tag(session, name=form.get("name"), color=form.get("color", "#3498db"))
        from app.services.audit_service import log_action
        await log_action(session, user['sub'], "Create Tag", f"Name: {form.get('name')}")
    return RedirectResponse(url="/crm/tags", status_code=302)


@router.get("/api/crm/stats")
async def api_crm_stats(user: dict = Depends(require_auth)):
    async with async_session_maker() as session:
        businesses_count = await get_businesses_count(session)
        customers_count = await get_customers_count(session)
    
    return JSONResponse({
        "businesses": businesses_count,
        "customers": customers_count,
    })