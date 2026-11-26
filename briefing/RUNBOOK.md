# Nightly Runbook: Morning Policy Briefing

You are producing Josh's Morning Policy Briefing for today's date (Eastern time).
Work through the steps in order. The finished page must be published by **5:00 a.m. Eastern**.
No one is awake to answer questions, so don't stop to ask. Make the call and keep going.

## 1. The job

Find political news **of real substance**: what policies actually do and who they affect.

- **Include:** bills passed, signed, or advancing out of committee; laws taking effect;
  regulations proposed or finalized; executive orders; court rulings that change what a
  policy does; agency guidance; budget decisions; ballot questions; and new data or official
  reports that change the picture of a policy's effects.
- **Skip:** horse-race coverage, polls, fundraising, campaign strategy, who is "winning",
  feuds, insults, personnel drama with no policy consequence, and speculation about political
  motives. If a story is half substance and half politics, keep the substance and drop the rest.

## 2. Coverage

Three sections, in this order:

1. **Federal**: Congress, the White House, federal agencies, and federal courts.
2. **Massachusetts**: the Legislature (General Court), Governor, state agencies, courts,
   ballot questions, and major municipal policy with statewide reach.
3. **New Hampshire**: the General Court, Governor, state agencies, courts, and the same
   kinds of local stories.

**Priority topics** are labor, healthcare, and education. Search for these deliberately in
every section. Also include any other story of genuine policy substance (housing, energy,
taxes, immigration, criminal justice, environment, transportation, technology, and so on).

**Target length:** 15–25 stories in total. Federal will usually be the largest section.
Aim for at least 3–4 stories each for Massachusetts and New Hampshire when the news supports
it. Never pad: on a quiet day (a weekend or holiday) it is fine to go shorter, and to say so in
the `note`. A state section may be empty if nothing substantive happened.

**Freshness:** focus on the last ~24 hours (on Mondays, the weekend too). An older story can
come in only when something new happened today, such as a law taking effect or a deadline
arriving.

## 3. Sources

- **Search widely.** Use many queries: by topic, by state, by agency, and by outlet. Don't
  stop at the first few results. Good habits:
  - priority topics × each section (e.g. "Massachusetts health care bill", "NH education
    funding", "Department of Labor rule");
  - state-specific outlets by name (State House News Service, CommonWealth Beacon, WBUR,
    Boston Globe, NH Bulletin, NHPR, Union Leader, InDepthNH, Concord Monitor);
  - primary sources: federalregister.gov, congress.gov, mass.gov, malegislature.gov,
    gc.nh.gov, governor press releases, and court opinions.
- **Read the article** (or the primary document) before summarizing it. Don't write from
  search snippets alone.
- **Cover the spectrum deliberately.** Each briefing should cite outlets from the left, the
  center, and the right (see `briefing/outlets.json` for lean). For major federal stories,
  check how at least one right-leaning and one left-leaning outlet covered them, and cite
  both when they add facts. Wire services (AP, Reuters) and primary documents are the
  backbone. Partisan outlets are supplements.
- **Corroborate.** Prefer stories confirmed by a highly rated outlet or an official
  document. If a story appears only in a mixed- or low-rated outlet, include it only if it is
  genuinely important. The page will flag it automatically. In the text, say plainly that
  the information comes from that outlet ("According to the Washington Examiner, …").

### Reliability ratings and the labeling rule

`briefing/outlets.json` lists outlets with their lean and reliability (from Media Bias/Fact
Check and Ad Fontes Media). The page labels every source from that file. **The less reliable
the source, the more prominently the page states where the information comes from and how the
outlet is rated.** The build script handles the visual labels. Your job is to:

1. Attribute claims in the text whenever a story relies on anything below a highly rated outlet.
2. **Cite an outlet that isn't in `outlets.json`:** look up its ratings (search
   "<outlet> Media Bias Fact Check" and "<outlet> Ad Fontes Media") and **add it to
   `outlets.json`** with `checked` set to today. If you can't find ratings, add it with tier
   `"unrated"`. The page will then warn readers.
3. **Cite an outlet whose `checked` is `null` or more than a year old:** confirm its ratings
   the same way and update the entry (fix anything wrong and set `checked` to today). Limit
   this to at most ~5 outlets per night so the briefing still finishes on time.

Tier guide: `primary` = official government record; `high` = MBFC High/Very High factual and
Ad Fontes reliable; `mostly` = Mostly Factual; `mixed` = Mixed factual; `low` = Low/Very Low
factual or flagged Questionable; `unrated` = no ratings found.

## 4. Rules for writing

- **Plain language.** Write for a smart reader who isn't a policy specialist. Define jargon
  the first time ("reconciliation, a budget process that needs only a simple majority in the
  Senate").
- **Substance only:** what changed, what it does, who it affects. Use concrete numbers when
  the sources give them (dollars, number of people, effective dates).
- **No speculation about political winners and losers.** No "a win for", "a blow to",
  "a political gamble", or "sets up a fight". Describe positions by what they would do, not by
  who gains politically. When the parties disagree about a policy's effects, state each side's
  claim neutrally and attribute it.
- **Neutral headlines:** factual, specific, and without loaded verbs ("slams", "guts",
  "rams through").
- **Every story links to its source(s).** Use the article's own URL, not a homepage or search
  page. Check that each URL is the one you actually read.
- Status line: a short phrase such as "Signed into law", "Passed House 220–211",
  "Proposed rule; comments due Jan. 20", "Court ruling", or "Takes effect Jan. 1".

## 5. Write the data file

Save today's briefing as `data/YYYY-MM-DD.json` (today's Eastern date):

```json
{
  "date": "2026-11-27",
  "generated_at": "2026-11-27 3:41 a.m. ET",
  "note": "Optional one or two sentences, e.g. holiday slowdown. Omit if not needed.",
  "sections": {
    "federal": [ STORY, ... ],
    "massachusetts": [ STORY, ... ],
    "new_hampshire": [ STORY, ... ]
  }
}
```

Each STORY:

```json
{
  "headline": "Labor Department proposes new overtime threshold of $X",
  "topic": "labor",
  "status": "Proposed rule; comments due Jan. 20",
  "what_changed": "One to three sentences.",
  "what_it_does": "One to four sentences on the mechanics.",
  "who_it_affects": "One to three sentences, concrete groups and numbers.",
  "whats_next": "Optional: next vote, effective date, deadline.",
  "sources": [
    {"url": "https://apnews.com/article/...", "title": "Article headline as published"},
    {"url": "https://www.federalregister.gov/documents/...", "title": "Proposed rule text"}
  ],
  "source_note": "Optional: e.g. 'Only one outlet has reported this so far.'"
}
```

- `topic` is one of `labor`, `healthcare`, `education`, or `other`. For `other`, add
  `"topic_label": "Housing"` (or a similar short label).
- The build script puts labor, healthcare, and education first in each section
  automatically. Within that, put the most consequential stories first.
- A source from an outlet not in `outlets.json` should get its own entry there (see §3).
  As a last resort, give the source `"outlet"` and a `"rating"` object
  (`lean`, `tier`, `mbfc`, `adfontes`).

## 6. Build, check, publish

```bash
python3 scripts/build.py data/YYYY-MM-DD.json
```

- If it prints `FAILED`, fix the data file and run it again.
- Then commit and push to the `main` branch (the website serves from `main`):

```bash
git add data docs briefing/outlets.json
git commit -m "Briefing for YYYY-MM-DD"
git push origin HEAD:main
```

If the push is rejected because `main` moved, run `git pull --rebase origin main`, rebuild,
and push again. Never force-push.

## 7. Final self-check (before pushing)

- [ ] Each story says what changed, what it does, and who it's affected, in plain words.
- [ ] No horse-race language and no predictions about who wins politically.
- [ ] Every story has at least one working link to the article you actually read.
- [ ] Left, center, and right outlets all appear somewhere in the briefing.
- [ ] Stories from mixed/low/unrated outlets attribute their claims in the text.
- [ ] Federal, Massachusetts, and New Hampshire are all covered (or noted as quiet).
