import logging
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User

logger = logging.getLogger(__name__)

async def get_top_referrers(session: AsyncSession, limit: int = 10):
    """Eng ko'p referal yig'gan foydalanuvchilarni olish."""
    try:
        query = (
            select(User)
            .where(User.referral_count > 0)
            .order_by(desc(User.referral_count))
            .limit(limit)
        )
        result = await session.execute(query)
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get top referrers: {e}")
        return []

async def get_user_referral_stats(session: AsyncSession, user_id: int):
    """Foydalanuvchining referal statistikasini olish."""
    try:
        user = await session.execute(select(User).where(User.user_id == user_id))
        user_obj = user.scalar_one_or_none()
        if not user_obj:
            return None
        
        # Count actual registered referrals if needed, 
        # but we use referral_count column for performance
        return {
            "referral_count": user_obj.referral_count,
            "added_users_count": user_obj.added_users_count,
            "rank": await get_user_rank(session, user_id)
        }
    except Exception as e:
        logger.error(f"Failed to get referral stats for {user_id}: {e}")
        return None

async def get_user_rank(session: AsyncSession, user_id: int):
    """Foydalanuvchining referallar bo'yicha o'rnini aniqlash."""
    try:
        user_res = await session.execute(select(User.referral_count).where(User.user_id == user_id))
        user_count = user_res.scalar_one_or_none()
        if user_count is None:
            return 0
        
        rank_query = select(func.count(User.id)).where(User.referral_count > user_count)
        rank_res = await session.execute(rank_query)
        return rank_res.scalar_one() + 1
    except Exception as e:
        logger.error(f"Failed to get rank for {user_id}: {e}")
        return 0
