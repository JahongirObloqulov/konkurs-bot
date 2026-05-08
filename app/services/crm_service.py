from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, Customer, Interaction, Tag, CustomerTag


async def create_business(
    session: AsyncSession,
    name: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    address: Optional[str] = None,
    description: Optional[str] = None,
    created_by: int = 0,
) -> Business:
    business = Business(
        name=name,
        phone=phone,
        email=email,
        address=address,
        description=description,
        created_by=created_by,
    )
    session.add(business)
    await session.commit()
    await session.refresh(business)
    return business


async def get_all_businesses(session: AsyncSession) -> list[Business]:
    result = await session.execute(select(Business).order_by(Business.created_at.desc()))
    return result.scalars().all()


async def get_business_by_id(session: AsyncSession, business_id: int) -> Optional[Business]:
    result = await session.execute(select(Business).where(Business.id == business_id))
    return result.scalar_one_or_none()


async def update_business(
    session: AsyncSession,
    business_id: int,
    **kwargs,
) -> Optional[Business]:
    business = await get_business_by_id(session, business_id)
    if not business:
        return None
    for key, value in kwargs.items():
        if value is not None:
            setattr(business, key, value)
    await session.commit()
    await session.refresh(business)
    return business


async def delete_business(session: AsyncSession, business_id: int) -> bool:
    business = await get_business_by_id(session, business_id)
    if not business:
        return False
    await session.delete(business)
    await session.commit()
    return True


async def create_customer(
    session: AsyncSession,
    business_id: int,
    full_name: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    notes: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Customer:
    customer = Customer(
        business_id=business_id,
        user_id=user_id,
        full_name=full_name,
        phone=phone,
        email=email,
        notes=notes,
    )
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return customer


async def get_customers_by_business(session: AsyncSession, business_id: int) -> list[Customer]:
    result = await session.execute(
        select(Customer).where(Customer.business_id == business_id).order_by(Customer.created_at.desc())
    )
    return result.scalars().all()


async def get_customer_by_id(session: AsyncSession, customer_id: int) -> Optional[Customer]:
    result = await session.execute(select(Customer).where(Customer.id == customer_id))
    return result.scalar_one_or_none()


async def update_customer(session: AsyncSession, customer_id: int, **kwargs) -> Optional[Customer]:
    customer = await get_customer_by_id(session, customer_id)
    if not customer:
        return None
    for key, value in kwargs.items():
        if value is not None:
            setattr(customer, key, value)
    await session.commit()
    await session.refresh(customer)
    return customer


async def delete_customer(session: AsyncSession, customer_id: int) -> bool:
    customer = await get_customer_by_id(session, customer_id)
    if not customer:
        return False
    await session.delete(customer)
    await session.commit()
    return True


async def create_interaction(
    session: AsyncSession,
    customer_id: int,
    interaction_type: str,
    description: Optional[str] = None,
    created_by: int = 0,
) -> Interaction:
    interaction = Interaction(
        customer_id=customer_id,
        interaction_type=interaction_type,
        description=description,
        created_by=created_by,
    )
    session.add(interaction)
    await session.commit()
    await session.refresh(interaction)
    return interaction


async def get_interactions_by_customer(session: AsyncSession, customer_id: int) -> list[Interaction]:
    result = await session.execute(
        select(Interaction).where(Interaction.customer_id == customer_id).order_by(Interaction.created_at.desc())
    )
    return result.scalars().all()


async def get_all_tags(session: AsyncSession) -> list[Tag]:
    result = await session.execute(select(Tag).order_by(Tag.name))
    return result.scalars().all()


async def create_tag(session: AsyncSession, name: str, color: str = "#3498db") -> Tag:
    tag = Tag(name=name, color=color)
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return tag


async def add_tag_to_customer(session: AsyncSession, customer_id: int, tag_id: int) -> bool:
    existing = await session.execute(
        select(CustomerTag).where(
            CustomerTag.customer_id == customer_id,
            CustomerTag.tag_id == tag_id,
        )
    )
    if existing.scalar_one_or_none():
        return False
    ct = CustomerTag(customer_id=customer_id, tag_id=tag_id)
    session.add(ct)
    await session.commit()
    return True


async def remove_tag_from_customer(session: AsyncSession, customer_id: int, tag_id: int) -> bool:
    result = await session.execute(
        select(CustomerTag).where(
            CustomerTag.customer_id == customer_id,
            CustomerTag.tag_id == tag_id,
        )
    )
    ct = result.scalar_one_or_none()
    if not ct:
        return False
    await session.delete(ct)
    await session.commit()
    return True


async def get_customers_count(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(Customer.id)))
    return result.scalar_one() or 0


async def get_businesses_count(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(Business.id)))
    return result.scalar_one() or 0