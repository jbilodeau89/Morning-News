# Morning Policy Briefing

A daily briefing on policy substance (what changed, what it does, and who it affects) for
federal, Massachusetts, and New Hampshire government. Labor, health care, and education
come first.

## How it works

1. **Every night at about 3:15 a.m. Eastern**, a Claude scheduled task wakes up on Josh's
   Claude plan.
2. Claude follows the instructions in `briefing/RUNBOOK.md`. It searches widely, reads the
   articles, checks each outlet's reliability and lean, and writes the stories.
3. A small program (`scripts/build.py`) turns the stories into the web page. It enforces the
   labeling rule automatically: the weaker an outlet's rating, the more prominent the warning.
4. The page is published to GitHub Pages, ready well before 5:00 a.m.

## What's where

| File | What it is |
| --- | --- |
| `briefing/RUNBOOK.md` | The editorial rules and nightly steps. **Edit this to change what the briefing covers or how it's written.** |
| `briefing/outlets.json` | The list of news outlets with their lean and reliability ratings. |
| `data/` | Each day's stories, saved as data. |
| `docs/` | The web pages themselves (today's page and past briefings). |
| `scripts/build.py` | Builds the page from the data. |

## Changing things

The easiest way is to open a Claude Code session on this repository and say what you want,
for example "add Maine to the coverage", "fewer federal stories", or "always include a
Supreme Court section". Claude will update the runbook (and the page design, if needed).

## If a morning's briefing is missing

The page shows a yellow banner whenever it's displaying an older day's briefing. If you see
it, open the Claude app and check the scheduled task **Morning Policy Briefing** for its last
run. Usually one missed run fixes itself the next night.
