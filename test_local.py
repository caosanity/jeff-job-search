"""
test_local.py — Local test for job_search.py pipeline.
Uses hardcoded sample jobs (no JSearch key needed) and prints to console (no SMTP needed).
Tests: resume loading, Claude ranking, HTML generation.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from job_search import load_resume_from_claude_md, fetch_all_jobs, rank_jobs_with_claude, build_email_html


def main():
    print("=== LOCAL TEST — job_search.py pipeline ===\n")

    print("[1/3] Loading resume from CLAUDE.md...")
    resume = load_resume_from_claude_md()
    print(f"      Resume loaded ({len(resume)} chars)\n")

    print("[2/3] Fetching real Toronto job postings from JSearch...")
    jobs = fetch_all_jobs()
    if not jobs:
        print("      No jobs fetched — check JSEARCH_API_KEY.")
        return
    print(f"      Fetched {len(jobs)} unique postings\n")

    print(f"[3/3] Sending {len(jobs)} jobs to Claude for ranking...")
    ranked = rank_jobs_with_claude(jobs, resume)
    print(f"      Claude returned {len(ranked)} ranked jobs\n")

    print("Results:\n")
    for i, job in enumerate(ranked, 1):
        score = job.get("match_score", "?")
        print(f"  #{i}  [{score}/10]  {job.get('title')}  —  {job.get('company')}")
        print(f"       Salary: {job.get('salary', 'Not listed')}")
        print(f"       Why: {job.get('match_reason', '')}")
        print(f"       Apply: {job.get('apply_link', '')}")
        print()

    print("Building HTML email preview...")
    html = build_email_html(ranked)
    out = "test_email_preview.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"      Saved to {out} — open in a browser to preview the email layout.\n")

    print("=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
