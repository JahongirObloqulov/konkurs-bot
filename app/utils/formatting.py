from app.db.models import Contest, Winner


def format_contest_view(contest: Contest, participants_count: int) -> str:
    status = "\u2705 Faol" if contest.is_active else "\u274c Tugagan"
    return (
        f"\U0001f3c6 <b>{contest.title}</b>\n\n"
        f"\U0001f4dd {contest.description}\n\n"
        f"\U0001f381 <b>Sovg'a:</b> {contest.prize}\n"
        f"\U0001f465 <b>Ishtirokchilar:</b> {participants_count}\n"
        f"\U0001f3c5 <b>G'oliblar soni:</b> {contest.winners_count}\n"
        f"\U0001f4ca <b>Holat:</b> {status}\n"
    )


def format_results_view(contest: Contest, winners: list[Winner]) -> str:
    text = f"\U0001f3c6 <b>{contest.title} - Natijalar</b>\n\n\U0001f3c5 <b>G'oliblar:</b>\n\n"
    for i, winner in enumerate(winners, 1):
        mention = f"@{winner.username}" if winner.username else winner.full_name
        text += f"{i}. {mention} ({winner.full_name})\n"
    text += f"\n\U0001f381 <b>Sovg'a:</b> {contest.prize}"
    return text
