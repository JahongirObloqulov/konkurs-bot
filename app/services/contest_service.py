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
) -> Contest | None:
    try:
        contest = Contest(
            title=title,
            description=description,
            prize=prize,
            winners_count=winners_count,
            created_by=created_by,
            require_subscription=require_subscription,
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
        existing_winners = await get_winners(session, contest_id)
        if existing_winners:
            return existing_winners

        contest = await get_contest_by_id(session, contest_id)
        if not contest or not contest.is_active:
            return []

        participants = await get_participants(session, contest_id)
        if not participants:
            return []

        count = min(contest.winners_count, len(participants))
        selected = random.sample(participants, count)

        winners: list[Winner] = []
        for p in selected:
            winner = Winner(
                contest_id=contest_id,
                user_id=p.user_id,
                username=p.username,
                full_name=p.full_name,
            )
            session.add(winner)
            winners.append(winner)

        contest.is_active = False
        contest.ended_at = datetime.now(timezone.utc)
        await session.commit()
        logger.info(f"Winners selected for contest {contest_id}: {len(winners)} winners")

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
