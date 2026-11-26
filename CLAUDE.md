# Morning Policy Briefing

This repository produces Josh's daily policy briefing web page.

- **Nightly run:** follow `briefing/RUNBOOK.md` step by step. It is the full editorial and
  publishing procedure. Don't ask questions during a nightly run; no one is awake to answer.
- **Ratings:** `briefing/outlets.json` (outlet lean and reliability). Keep it current as the
  runbook describes.
- **Page builder:** `python3 scripts/build.py data/YYYY-MM-DD.json` validates the day's data
  and writes `docs/` (served by GitHub Pages from the `main` branch).

Josh is not a programmer. When talking with him, use plain language and skip code details.
