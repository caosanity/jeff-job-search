"""
job_search.py — Weekly Toronto Job Search Digest
Reads resume from CLAUDE.md, searches for matching jobs, emails top 10 to Jeff.

Run manually:  python job_search.py
Run via cron:  0 9 * * 6 cd /path/to/jeff-job-workflow && python job_search.py
"""

import os
import re
import json
import smtplib
import logging
import requests
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIGURATION — edit these as needed
# ─────────────────────────────────────────────
RECIPIENT_EMAIL = "jeffcao88@outlook.com"
LOCATION        = "Toronto, ON"
NUM_RESULTS     = 10

JOB_TITLES = [
    "Product Owner",
    "Product Manager",
    "Technical Product Manager",
    "AI Product Manager",
    "Senior Product Owner",
]

# Email (SMTP) settings — set via environment variables for security
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER")      # e.g. yourname@gmail.com
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")  # App password, not your login password

# Anthropic API key for resume-to-job matching
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Job board APIs — set whichever you have access to
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY")  # RapidAPI JSearch (recommended, free tier)
ADZUNA_APP_ID   = os.getenv("ADZUNA_APP_ID")    # Optional: Adzuna API
ADZUNA_API_KEY  = os.getenv("ADZUNA_API_KEY")

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/job_search.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# STEP 1: Read resume from CLAUDE.md
# ─────────────────────────────────────────────
def load_resume_from_claude_md() -> str:
    """Parse the resume block from CLAUDE.md so any edit there flows through automatically."""
    claude_md = Path("CLAUDE.md").read_text()
    match = re.search(r"## Resume.*?```(.*?)```", claude_md, re.DOTALL)
    if not match:
        raise ValueError("Could not find resume block in CLAUDE.md. Make sure it's wrapped in triple backticks under '## Resume'.")
    resume = match.group(1).strip()
    log.info("Resume loaded from CLAUDE.md (%d chars)", len(resume))
    return resume


# ─────────────────────────────────────────────
# STEP 2: Fetch job postings
# ─────────────────────────────────────────────
def fetch_jobs_jsearch(title: str, location: str) -> list[dict]:
    """Fetch jobs using JSearch API (via RapidAPI). Free tier: 200 req/month."""
    if not JSEARCH_API_KEY:
        log.warning("JSEARCH_API_KEY not set — skipping JSearch for '%s'", title)
        return []

    url = "https://jsearch.p.rapidapi.com/search"
    params = {
        "query": f"{title} in {location}",
        "num_pages": "1",
        "date_posted": "week",
        "country": "ca",
    }
    headers = {
        "X-RapidAPI-Key": JSEARCH_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as e:
        log.error("JSearch error for '%s': %s", title, e)
        return []


def fetch_jobs_adzuna(title: str, location: str) -> list[dict]:
    """Fetch jobs using Adzuna API (free tier available)."""
    if not ADZUNA_APP_ID or not ADZUNA_API_KEY:
        return []

    url = f"https://api.adzuna.com/v1/api/jobs/ca/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_API_KEY,
        "results_per_page": 10,
        "what": title,
        "where": location,
        "sort_by": "date",
        "content-type": "application/json",
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        raw = r.json().get("results", [])
        # Normalise to JSearch-like shape
        return [
            {
                "job_title": j.get("title"),
                "employer_name": j.get("company", {}).get("display_name"),
                "job_city": location,
                "job_posted_at_datetime_utc": j.get("created"),
                "job_apply_link": j.get("redirect_url"),
                "job_description": j.get("description", ""),
                "job_min_salary": j.get("salary_min"),
                "job_max_salary": j.get("salary_max"),
            }
            for j in raw
        ]
    except Exception as e:
        log.error("Adzuna error for '%s': %s", title, e)
        return []


def fetch_all_jobs() -> list[dict]:
    """Collect raw postings from all configured sources, deduplicate by title+company."""
    raw = []
    for title in JOB_TITLES:
        raw.extend(fetch_jobs_jsearch(title, LOCATION))
        raw.extend(fetch_jobs_adzuna(title, LOCATION))

    # Deduplicate
    seen, unique = set(), []
    for job in raw:
        key = (
            (job.get("job_title") or "").lower(),
            (job.get("employer_name") or "").lower(),
        )
        if key not in seen:
            seen.add(key)
            unique.append(job)

    log.info("Fetched %d unique job postings", len(unique))
    return unique


# ─────────────────────────────────────────────
# STEP 3: Score & rank with Claude
# ─────────────────────────────────────────────
def rank_jobs_with_claude(jobs: list[dict], resume: str) -> list[dict]:
    """Send jobs + resume to Claude API; get back a ranked top-10 with match reasons."""
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")

    jobs_text = json.dumps(
        [
            {
                "title": j.get("job_title"),
                "company": j.get("employer_name"),
                "location": j.get("job_city"),
                "posted": j.get("job_posted_at_datetime_utc"),
                "description": (j.get("job_description") or "")[:800],
                "salary_min": j.get("job_min_salary"),
                "salary_max": j.get("job_max_salary"),
                "apply_link": j.get("job_apply_link"),
            }
            for j in jobs
        ],
        indent=2,
    )

    prompt = f"""You are a career advisor helping Jeff Cao find the best Product Owner / Product Manager roles in Toronto.

## Jeff's Resume
{resume}

## Job Postings (JSON)
{jobs_text}

## Task
Return the top {NUM_RESULTS} best-matching jobs as a JSON array. For each job include:
- title
- company
- location
- posted_date
- salary (format as range string or "Not listed")
- apply_link
- match_score (1–10)
- match_reason (2–3 sentences explaining why this fits Jeff's background)

Rank by match_score descending. Return ONLY valid JSON — no markdown, no preamble."""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 4000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    raw_text = response.json()["content"][0]["text"].strip()

    # Strip any accidental markdown fences
    raw_text = re.sub(r"^```json\s*|^```\s*|```$", "", raw_text, flags=re.MULTILINE).strip()
    ranked = json.loads(raw_text)
    log.info("Claude returned %d ranked jobs", len(ranked))
    return ranked


# ─────────────────────────────────────────────
# STEP 4: Build HTML email
# ─────────────────────────────────────────────
def build_email_html(jobs: list[dict]) -> str:
    today = datetime.now().strftime("%B %d, %Y")
    cards = ""
    for i, job in enumerate(jobs, 1):
        score = job.get("match_score", "–")
        score_color = "#2ecc71" if score >= 8 else "#f39c12" if score >= 6 else "#e74c3c"
        cards += f"""
        <tr>
          <td style="padding:20px 0; border-bottom:1px solid #eee;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <span style="font-size:12px;color:#999;">#{i}</span>
                  <span style="margin-left:8px;background:{score_color};color:#fff;
                    font-size:11px;font-weight:bold;padding:2px 8px;border-radius:12px;">
                    {score}/10 match
                  </span>
                  <h2 style="margin:8px 0 2px;font-size:18px;color:#1a1a1a;">
                    {job.get('title', 'N/A')}
                  </h2>
                  <p style="margin:0;font-size:14px;color:#555;">
                    {job.get('company', 'N/A')} &nbsp;·&nbsp; {job.get('location', LOCATION)}
                  </p>
                  <p style="margin:4px 0;font-size:13px;color:#888;">
                    💰 {job.get('salary', 'Not listed')} &nbsp;·&nbsp;
                    📅 {job.get('posted_date', 'Recent')}
                  </p>
                  <p style="margin:10px 0;font-size:14px;color:#333;line-height:1.5;">
                    {job.get('match_reason', '')}
                  </p>
                  <a href="{job.get('apply_link', '#')}"
                     style="display:inline-block;margin-top:8px;padding:8px 20px;
                       background:#0070f3;color:#fff;border-radius:6px;
                       text-decoration:none;font-size:13px;font-weight:600;">
                    Apply Now →
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
        <!-- Header -->
        <tr>
          <td style="background:#0070f3;padding:32px 40px;">
            <h1 style="margin:0;color:#fff;font-size:24px;">Your Weekly Job Digest</h1>
            <p style="margin:8px 0 0;color:rgba(255,255,255,0.8);font-size:14px;">
              Top {NUM_RESULTS} Toronto matches · {today}
            </p>
          </td>
        </tr>
        <!-- Jobs -->
        <tr>
          <td style="padding:0 40px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              {cards}
            </table>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="padding:24px 40px;background:#fafafa;border-top:1px solid #eee;">
            <p style="margin:0;font-size:12px;color:#999;text-align:center;">
              Sent automatically every Saturday at 9:00 AM ET · Update your resume in
              <code>CLAUDE.md</code> to refresh these results.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ─────────────────────────────────────────────
# STEP 5: Send email
# ─────────────────────────────────────────────
def send_email(html: str):
    if not SMTP_USER or not SMTP_PASSWORD:
        raise EnvironmentError("SMTP_USER and SMTP_PASSWORD must be set as environment variables.")

    today = datetime.now().strftime("%B %d, %Y")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🏙️ Your Top 10 Toronto Job Matches — {today}"
    msg["From"]    = SMTP_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, RECIPIENT_EMAIL, msg.as_string())

    log.info("Email sent to %s", RECIPIENT_EMAIL)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    log.info("=== Job search workflow started ===")

    resume = load_resume_from_claude_md()
    jobs   = fetch_all_jobs()

    if not jobs:
        log.error("No jobs fetched — check your API keys. Aborting.")
        return

    top_jobs = rank_jobs_with_claude(jobs, resume)
    html     = build_email_html(top_jobs)
    send_email(html)

    log.info("=== Workflow complete ===")


if __name__ == "__main__":
    main()
