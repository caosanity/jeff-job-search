# Jeff's Weekly Job Search — Setup Guide

## What This Does

Every **Saturday at 9:00 AM ET**, this workflow:
1. Reads your resume from `CLAUDE.md`
2. Searches Toronto job boards for Product Owner / PM roles
3. Uses Claude AI to rank the top 10 matches against your resume
4. Emails a formatted digest to jeffcao88@outlook.com

**To update your resume:** edit the `## Resume` section in `CLAUDE.md`. Everything else updates automatically.

---

## Quick Setup (15 minutes)

### 1. Get your API keys

| Key | Where to get it | Free tier? |
|---|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com | Pay-per-use |
| `JSEARCH_API_KEY` | https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch | 200 req/mo free |
| `SMTP_USER` | Your Gmail address | Free |
| `SMTP_PASSWORD` | Gmail → Settings → App Passwords | Free |

> **Gmail App Password:** Go to myaccount.google.com → Security → 2-Step Verification → App Passwords. Generate one for "Mail".

### 2. Option A — Run locally with cron

```bash
# 1. Clone or download this folder
# 2. Set your environment variables (add to ~/.zshrc or ~/.bashrc):
export ANTHROPIC_API_KEY="sk-ant-..."
export JSEARCH_API_KEY="your-rapidapi-key"
export SMTP_USER="youremail@gmail.com"
export SMTP_PASSWORD="your-app-password"

# 3. Install dependencies
pip install requests

# 4. Test it manually first
python job_search.py

# 5. Add to crontab (crontab -e):
# 0 9 * * 6 cd /path/to/jeff-job-workflow && python job_search.py >> logs/job_search.log 2>&1
```

### 2. Option B — Run on GitHub Actions (recommended — no laptop needed)

```bash
# 1. Create a new private GitHub repo
# 2. Push this folder to it
git init && git add . && git commit -m "init" && git push

# 3. Add secrets: repo → Settings → Secrets and variables → Actions
#    Add each key from the table above as a Repository Secret

# 4. That's it — runs automatically every Saturday at 9 AM ET
#    You can also trigger manually from Actions tab → "Weekly Job Search Digest" → Run workflow
```

---

## Updating Your Resume

1. Open `CLAUDE.md`
2. Find the `## Resume` section
3. Edit the text inside the triple backticks
4. Commit and push (if using GitHub Actions)

The next Saturday run will automatically use the updated resume.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No email received | Check `logs/job_search.log`; verify SMTP credentials |
| No jobs found | Check `JSEARCH_API_KEY`; you may have hit the free tier limit |
| Claude ranking fails | Check `ANTHROPIC_API_KEY`; ensure you have API credits |
| Wrong timezone | Adjust cron to `0 14 * * 6` for EST (winter) |
