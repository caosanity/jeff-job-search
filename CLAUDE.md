# Weekly Job Search Automation

Every **Saturday at 9:00 AM ET**, run the job search workflow script to find the top 10 Toronto job postings matching the resume below and email them to jeffcao88@outlook.com.

---

## How to Run

```bash
python job_search.py
```

Or via cron (already configured — see Setup below).

---

## Resume (Source of Truth)

Update this section whenever your resume changes. The script reads this directly to tailor the search.

```
NAME: Jeff Cao
EMAIL: jeffcao88@outlook.com

CURRENT ROLE: Product Owner, Data Automation, Architecture, and A.I Pod — Canada Goose Holdings Inc. (April 2025–Present)
- Owned full product lifecycle across two scrum teams (15+ developers) spanning Data Engineering and Systems Integration
- Prototyped AI-powered release notes agent in Copilot Studio; adopted company-wide
- 95%+ business stakeholder satisfaction score every Program Increment

PREVIOUS ROLES:
- Product Owner, OneView Team — Bell Mobility Inc. (July 2023–Mar 2025)
  - Led eSIM as Primary initiative; 50% eSIM adoption rate at retail
  - Managed scrum team for residential solutions; 20% quicker quote creation
- Business Analyst/Project Manager — Foxquilt Insurance Services Inc. (Sept 2021–Mar 2023)
  - Launched first Workers' Compensation product across 46 US states
  - 100% on-time production deployments for one year; 20% increase in policies sold

PROJECTS:
- AI Golf Caddy: RAG + LLM web app delivering personalized golf strategies
- Product Case Study: AI-assisted driving range ball allocation web app

SKILLS:
- AI/ML: LLMs, RAG, Prompt Engineering, Evaluation Methods, AI Product Design, ML Lifecycle
- Product: Strategy, Roadmapping, Agile/SAFe, A/B Testing, KPI Definition, Stakeholder Management
- Technical: SQL, Python, APIs, Data Pipelines, Data Warehousing, Observability

CERTIFICATIONS:
- SAFe 6.0 AI Empowered Product Owner/Product Manager (POPM) — 2026

EDUCATION:
- University of Toronto — Hon. BSc Statistics, Statistical ML and Data Science (2017–2021)
```

---

## Target Job Roles

The script searches for these roles in Toronto (configurable in `job_search.py`):

- Product Owner
- Product Manager
- Technical Product Manager
- AI Product Manager
- Senior Product Owner

---

## Configuration

All settings live at the top of `job_search.py`:

| Variable | Default | Description |
|---|---|---|
| `RECIPIENT_EMAIL` | jeffcao88@outlook.com | Where to send the digest |
| `LOCATION` | Toronto, ON | Job search location |
| `NUM_RESULTS` | 10 | Number of job postings to include |
| `JOB_TITLES` | See above | List of roles to search |
| `SMTP_*` | See script | Email server settings |

To update your resume: edit the `RESUME` section above. The script reads from `CLAUDE.md` — so any change here automatically changes what the AI uses to rank and filter jobs.

---

## Cron Setup (Saturday 9:00 AM ET)

Add this to your crontab (`crontab -e`):

```cron
0 9 * * 6 cd /path/to/jeff-job-workflow && python job_search.py >> logs/job_search.log 2>&1
```

> **Note:** If your machine is not in the ET timezone, adjust the cron time accordingly (ET = UTC-5 in winter, UTC-4 in summer). Or use a cloud scheduler (see below).

### Alternative: Run on a Cloud Scheduler

If you want this to run without your laptop being on, deploy `job_search.py` to any cloud and schedule it:

- **GitHub Actions** — free, reliable (see `workflow.yml` in this folder)
- **AWS Lambda + EventBridge** — for AWS users
- **Google Cloud Scheduler + Cloud Run** — for GCP users

---

## Output

The email will contain:

- Job title and company
- Location and posting date
- Salary range (if listed)
- Match score (why it fits your resume)
- Direct link to apply

---

## Logs

All runs are logged to `logs/job_search.log`. Check here if a run fails or no email arrives.
