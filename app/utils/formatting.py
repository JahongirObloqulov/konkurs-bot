from app.db.models import Contest, Winner
from app.utils.translations import translate


def format_contest_view(contest: Contest, participants_count: int, lang: str = 'uz') -> str:
    status_text = translate('active', lang) if contest.is_active else translate('finished', lang)
    return (
        f"\U0001f3c6 <b>{contest.title}</b>\n\n"
        f"\U0001f4dd {contest.description}\n\n"
        f"\U0001f381 <b>{translate('prize', lang)}:</b> {contest.prize}\n"
        f"\U0001f465 <b>{translate('participants', lang)}:</b> {participants_count}\n"
        f"\U0001f3c5 <b>{translate('winners_count_label', lang)}:</b> {contest.winners_count}\n"
        f"\U0001f4ca <b>{translate('status', lang)}:</b> {status_text}\n"
    )


def format_results_view(contest: Contest, winners: list[Winner], lang: str = 'uz') -> str:
    results_title = translate('overview', lang) # or add a new key 'results'
    text = f"\U0001f3c6 <b>{contest.title} - {results_title}</b>\n\n\U0001f3c5 <b>{translate('winners_label', lang).upper()}:</b>\n\n"
    for i, winner in enumerate(winners, 1):
        mention = f"@{winner.username}" if winner.username else winner.full_name
        text += f"{i}. {mention} ({winner.full_name})\n"
    text += f"\n\U0001f381 <b>{translate('prize', lang)}:</b> {contest.prize}"
    return text
