"""
message_formatter.py — Rich message templates for Telegram and Discord.

Implemented in Phase 6 & 7: Notification Integrations.
"""

def format_telegram_message(job_data: dict) -> str:
    """Format a job posting as a Telegram HTML message."""
    title = job_data.get('position_title', 'Unknown Position')
    agency = job_data.get('agency', 'Unknown Agency')
    location = job_data.get('location', 'Unknown Location')
    salary_grade = job_data.get('salary_grade', 'N/A')
    monthly_salary = job_data.get('monthly_salary', 'N/A')
    deadline = job_data.get('application_deadline', 'Unknown Deadline')
    job_url = job_data.get('job_url', '#')

    # We use basic HTML tags supported by Telegram parse_mode='HTML'
    msg = f"🏛️ <b>New Job Posting</b>\n\n"
    msg += f"📌 <b>Position:</b> {title}\n"
    msg += f"🏢 <b>Agency:</b> {agency}\n"
    msg += f"📍 <b>Location:</b> {location}\n"
    msg += f"💰 <b>Salary:</b> SG {salary_grade} - {monthly_salary}\n"
    msg += f"⏳ <b>Deadline:</b> {deadline}\n\n"

    if job_url != '#':
        msg += f'<a href="{job_url}">🔗 View Full Details & Apply</a>'

    return msg

def format_discord_embed(job_data: dict) -> dict:
    """Format a job posting as a Discord embed payload."""
    title = job_data.get('position_title', 'Unknown Position')
    agency = job_data.get('agency', 'Unknown Agency')
    location = job_data.get('location', 'Unknown Location')
    salary_grade = job_data.get('salary_grade', 'N/A')
    monthly_salary = job_data.get('monthly_salary', 'N/A')
    deadline = job_data.get('application_deadline', 'Unknown Deadline')
    job_url = job_data.get('job_url', '#')

    # Discord blue color: 0x3498db (3447003 in decimal)
    if job_url == '#':
        job_url = "https://csc.gov.ph/career/"

    msg = f"📌 **Position:** {title}\n"
    msg += f"🏢 **Agency:** {agency}\n"
    msg += f"📍 **Location:** {location}\n"
    msg += f"💰 **Salary:** SG {salary_grade} - {monthly_salary}\n"
    msg += f"⏳ **Deadline:** {deadline}\n\n"
    msg += f"[🔗 View Full Details & Apply]({job_url})"

    embed_dict = {
        'title': "🏛️ New Job Posting",
        'url': job_url,
        'description': msg,
        'color': 3447003,
        'fields': []
    }

    return embed_dict

def format_daily_summary(jobs: list) -> str:
    """Format a daily summary of all new jobs found."""
    if not jobs:
        return "📊 <b>Daily CSC Job Summary</b>\n\nNo new jobs found matching your criteria today."

    msg = f"📊 <b>Daily CSC Job Summary</b>\n\n"
    msg += f"Found <b>{len(jobs)}</b> new job(s) matching your criteria:\n\n"

    for i, job in enumerate(jobs, 1):
        title = job.get('position_title', 'Unknown Position')
        agency = job.get('agency', 'Unknown Agency')
        msg += f"{i}. <b>{title}</b> at {agency}\n"

    return msg
