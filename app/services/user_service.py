from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    username: str | None,
    full_name: str,
) -> User:
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.username = username
        user.full_name = full_name
        await session.commit()
        return user

    user = User(user_id=user_id, username=username, full_name=full_name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_users_count(session: AsyncSession) -> int:
    from sqlalchemy import func

    result = await session.execute(select(func.count(User.id)))
    return result.scalar_one()


async def get_all_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User))
    return list(result.scalars().all())
