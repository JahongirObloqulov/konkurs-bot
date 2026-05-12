import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User

logger = logging.getLogger(__name__)


async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    username: str | None,
    full_name: str,
    referred_by_id: int | None = None,
) -> User | None:
    try:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.username = username
            user.full_name = full_name
            await session.commit()
            return user

        # Create new user
        user = User(
            user_id=user_id, 
            username=username, 
            full_name=full_name,
            referred_by_id=referred_by_id if referred_by_id != user_id else None
        )
        session.add(user)
        
        # Increment referral count for referrer
        if referred_by_id and referred_by_id != user_id:
            from sqlalchemy import update
            await session.execute(
                update(User)
                .where(User.user_id == referred_by_id)
                .values(referral_count=User.referral_count + 1)
            )
            
        await session.commit()
        await session.refresh(user)
        logger.info(f"New user registered: {user_id} (referred by: {referred_by_id})")
        return user
    except Exception as e:
        logger.error(f"Failed to get or create user {user_id}: {e}")
        await session.rollback()
        return None


async def increment_addition_count(session: AsyncSession, user_id: int):
    try:
        from sqlalchemy import update
        await session.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(added_users_count=User.added_users_count + 1)
        )
        await session.commit()
    except Exception as e:
        logger.error(f"Failed to increment addition count for {user_id}: {e}")
        await session.rollback()


async def get_users_count(session: AsyncSession) -> int:
    try:
        from sqlalchemy import func

        result = await session.execute(select(func.count(User.id)))
        return result.scalar_one()
    except Exception as e:
        logger.error(f"Failed to get users count: {e}")
        return 0
async def get_all_user_ids(session: AsyncSession) -> list[int]:
    try:
        result = await session.execute(select(User.user_id))
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Failed to get all user IDs: {e}")
        return []


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    """Foydalanuvchini Telegram ID orqali olish."""
    try:
        result = await session.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get user by id {user_id}: {e}")
        return None


async def update_user_language(session: AsyncSession, user_id: int, lang_code: str):
    """Foydalanuvchi tilini yangilash."""
    try:
        from sqlalchemy import update
        await session.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(language_code=lang_code)
        )
        await session.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to update language for {user_id}: {e}")
        await session.rollback()
        return False

