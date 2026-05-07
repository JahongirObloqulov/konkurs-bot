import random
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Contest, Participant, Winner


async def create_contest(
    session: AsyncSession,
    title: str,
    description: str,
    prize: str,
    winners_count: int,
    created_by: int,
    require_subscription: bool = True,
) -> Contest:
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
    return contest


async def get_active_contests(session: AsyncSession) -> list[Contest]:
    result = await session.execute(
        select(Contest).where(Contest.is_active.is_(True)).order_by(Contest.created_at.desc())
    )
    return list(result.scalars().all())


async def get_all_contests(session: AsyncSession) -> list[Contest]:
    result = await session.execute(select(Contest).order_by(Contest.created_at.desc()))
    return list(result.scalars().all())


async def get_contest_by_id(session: AsyncSession, contest_id: int) -> Contest | None:
    result = await session.execute(select(Contest).where(Contest.id == contest_id))
    return result.scalar_one_or_none()


async def end_contest(session: AsyncSession, contest_id: int) -> Contest | None:
    contest = await get_contest_by_id(session, contest_id)
    if contest:
        contest.is_active = False
        contest.ended_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(contest)
    return contest


async def delete_contest(session: AsyncSession, contest_id: int) -> bool:
    contest = await get_contest_by_id(session, contest_id)
    if contest:
        await session.delete(contest)
        await session.commit()
        return True
    return False


async def add_participant(
    session: AsyncSession,
    contest_id: int,
    user_id: int,
    username: str | None,
    full_name: str,
) -> Participant | None:
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
    return participant


async def get_participants_count(session: AsyncSession, contest_id: int) -> int:
    result = await session.execute(
        select(func.count(Participant.id)).where(Participant.contest_id == contest_id)
    )
    return result.scalar_one()


async def get_participants(session: AsyncSession, contest_id: int) -> list[Participant]:
    result = await session.execute(
        select(Participant).where(Participant.contest_id == contest_id)
    )
    return list(result.scalars().all())


async def select_winners(session: AsyncSession, contest_id: int) -> list[Winner]:
    contest = await get_contest_by_id(session, contest_id)
    if not contest:
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

    return winners


async def get_winners(session: AsyncSession, contest_id: int) -> list[Winner]:
    result = await session.execute(
        select(Winner).where(Winner.contest_id == contest_id)
    )
    return list(result.scalars().all())


async def is_participant(session: AsyncSession, contest_id: int, user_id: int) -> bool:
    result = await session.execute(
        select(Participant).where(
            Participant.contest_id == contest_id,
            Participant.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None
