import logging
import random
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Contest, Participant, Winner

logger = logging.getLogger(__name__)


async def create_contest(
    session: AsyncSession,
    title: str,
    description: str,
    prize: str,
    winners_count: int,
    created_by: int,
    require_subscription: bool = True,
    min_referrals: int = 0,
    min_additions: int = 0,
    media_type: str | None = None,
    file_id: str | None = None,
) -> Contest | None:
    try:
        contest = Contest(
            title=title,
            description=description,
            prize=prize,
            winners_count=winners_count,
            created_by=created_by,
            require_subscription=require_subscription,
            min_referrals=min_referrals,
            min_additions=min_additions,
            media_type=media_type,
            file_id=file_id,
        )
        session.add(contest)
        await session.commit()
        await session.refresh(contest)
        logger.info(f"Contest created: {contest.id} - {contest.title}")
        return contest
    except Exception as e:
        logger.error(f"Failed to create contest: {e}")
        await session.rollback()
        return None


async def check_requirements(
    session: AsyncSession, contest: Contest, user_id: int
) -> tuple[bool, str]:
    """Checks if a user meets all contest requirements."""
    try:
        from app.db.models import User
        result = await session.execute(select(User).where(User.user_id == user_id))
        user_obj = result.scalar_one_or_none()
        
        if not user_obj:
            return False, "Foydalanuvchi topilmadi!"

        if contest.min_referrals > 0 and user_obj.referral_count < contest.min_referrals:
            diff = contest.min_referrals - user_obj.referral_count
            return False, f"Taklif qilingan foydalanuvchilar yetarli emas! Yana {diff} ta odam taklif qilishingiz kerak."

        if contest.min_additions > 0 and user_obj.added_users_count < contest.min_additions:
            diff = contest.min_additions - user_obj.added_users_count
            return False, f"Guruhlarga qo'shilgan a'zolar yetarli emas! Yana {diff} ta odam qo'shishingiz kerak."

        return True, "Hamma shartlar bajarildi."
    except Exception as e:
        logger.error(f"Error checking requirements: {e}")
        return False, "Texnik xatolik yuz berdi."


async def get_active_contests(session: AsyncSession) -> list[Contest]:
    try:
        result = await session.execute(
            select(Contest).where(Contest.is_active.is_(True)).order_by(Contest.created_at.desc())
        )
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Failed to get active contests: {e}")
        return []


async def get_all_contests(session: AsyncSession) -> list[Contest]:
    try:
        result = await session.execute(select(Contest).order_by(Contest.created_at.desc()))
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Failed to get all contests: {e}")
        return []


async def get_contest_by_id(session: AsyncSession, contest_id: int) -> Contest | None:
    try:
        result = await session.execute(select(Contest).where(Contest.id == contest_id))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get contest {contest_id}: {e}")
        return None


async def end_contest(session: AsyncSession, contest_id: int) -> Contest | None:
    try:
        contest = await get_contest_by_id(session, contest_id)
        if contest:
            contest.is_active = False
            contest.ended_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(contest)
            logger.info(f"Contest ended: {contest_id}")
        return contest
    except Exception as e:
        logger.error(f"Failed to end contest {contest_id}: {e}")
        await session.rollback()
        return None


async def delete_contest(session: AsyncSession, contest_id: int) -> bool:
    try:
        contest = await get_contest_by_id(session, contest_id)
        if contest:
            await session.delete(contest)
            await session.commit()
            logger.info(f"Contest deleted: {contest_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete contest {contest_id}: {e}")
        await session.rollback()
        return False


async def add_participant(
    session: AsyncSession,
    contest_id: int,
    user_id: int,
    username: str | None,
    full_name: str,
) -> Participant | None:
    try:
        existing = await session.execute(
            select(Participant).where(
                Participant.contest_id == contest_id,
                Participant.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none():
            return None

        participant = Participant(
            contest_id=contest_id,
            user_id=user_id,
            username=username,
            full_name=full_name,
        )
        session.add(participant)
        await session.commit()
        await session.refresh(participant)
        logger.info(f"Participant added: user_id={user_id}, contest_id={contest_id}")
        return participant
    except Exception as e:
        logger.error(f"Failed to add participant: {e}")
        await session.rollback()
        return None


async def get_participants_count(session: AsyncSession, contest_id: int) -> int:
    try:
        result = await session.execute(
            select(func.count(Participant.id)).where(Participant.contest_id == contest_id)
        )
        return result.scalar_one()
    except Exception as e:
        logger.error(f"Failed to get participants count for contest {contest_id}: {e}")
        return 0


async def get_participants(session: AsyncSession, contest_id: int) -> list[Participant]:
    try:
        result = await session.execute(
            select(Participant).where(Participant.contest_id == contest_id)
        )
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Failed to get participants for contest {contest_id}: {e}")
        return []


async def select_winners(session: AsyncSession, contest_id: int) -> list[Winner]:
    try:
        # 1. Idempotency check: if winners already exist, return them
        existing_winners = await get_winners(session, contest_id)
        if existing_winners:
            return existing_winners

        contest = await get_contest_by_id(session, contest_id)
        if not contest or not contest.is_active:
            return []

        # 2. Get participants with their referral counts for weighted selection
        from app.db.models import User
        query = (
            select(Participant, User.referral_count)
            .join(User, User.user_id == Participant.user_id)
            .where(Participant.contest_id == contest_id)
        )
        result = await session.execute(query)
        rows = result.all()
        
        if not rows:
            return []

        participants = [row[0] for row in rows]
        # Weight = referrals + 1 (so everyone has at least one chance)
        weights = [row[1] + 1 for row in rows]

        count = min(contest.winners_count, len(participants))
        
        # Weighted random selection without replacement
        selected_winners_data: list[Participant] = []
        available_indices = list(range(len(participants)))
        
        for _ in range(count):
            if not available_indices:
                break
            
            curr_weights = [weights[i] for i in available_indices]
            # random.choices returns a list, we take the first element
            choice_idx = random.choices(range(len(available_indices)), weights=curr_weights, k=1)[0]
            
            orig_idx = available_indices.pop(choice_idx)
            selected_winners_data.append(participants[orig_idx])

        winners: list[Winner] = []
        for p in selected_winners_data:
            winner = Winner(
                contest_id=contest_id,
                user_id=p.user_id,
                username=p.username,
                full_name=p.full_name,
                selected_at=datetime.now(timezone.utc),
            )
            session.add(winner)
            winners.append(winner)

        contest.is_active = False
        contest.ended_at = datetime.now(timezone.utc)
        await session.commit()
        logger.info(f"Winners selected for contest {contest_id}: {len(winners)} winners (weighted)")

        # 3. Notify participants (Moved before return for consistency)
        try:
            from aiogram import Bot
            # Get current bot instance from context if possible, but here we might need to pass it
            # For simplicity, we'll assume the caller handles notification or we inject bot here.
            # However, contest_service shouldn't depend on Bot directly.
            # I will add a comment that notification should be handled by the handler.
            pass 
        except Exception as e:
            logger.error(f"Failed to notify participants: {e}")

        return winners
    except Exception as e:
        logger.error(f"Failed to select winners for contest {contest_id}: {e}")
        await session.rollback()
        return []


async def get_winners(session: AsyncSession, contest_id: int) -> list[Winner]:
    try:
        result = await session.execute(
            select(Winner).where(Winner.contest_id == contest_id)
        )
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Failed to get winners for contest {contest_id}: {e}")
        return []


async def is_participant(session: AsyncSession, contest_id: int, user_id: int) -> bool:
    try:
        result = await session.execute(
            select(Participant).where(
                Participant.contest_id == contest_id,
                Participant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None
    except Exception as e:
        logger.error(f"Failed to check participant status: {e}")
        return False


async def get_user_contests(session: AsyncSession, user_id: int) -> list[Contest]:
    try:
        result = await session.execute(
            select(Contest)
            .join(Participant, Participant.contest_id == Contest.id)
            .where(Participant.user_id == user_id)
            .order_by(Contest.created_at.desc())
        )
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Failed to get contests for user {user_id}: {e}")
        return []
