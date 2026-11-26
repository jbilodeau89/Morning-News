#!/usr/bin/env python3
"""Validate a day's briefing data and render the mobile web page.

Usage:
    python3 scripts/build.py                 # build from the newest file in data/
    (data format: see briefing/RUNBOOK.md, section 5)
    python3 scripts/build.py data/2026-11-26.json
    python3 scripts/build.py --check FILE    # validate only, write nothing

Outputs:
    docs/index.html                 newest briefing (what Josh opens)
    docs/archive/YYYY-MM-DD.html    a permanent copy of each day
    docs/archive/index.html         list of past briefings

Standard library only; no installs needed.
"""
from __future__ import annotations

import html
import json
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
OUTLETS = ROOT / "briefing" / "outlets.json"

SECTIONS = [
    ("federal", "Federal"),
    ("massachusetts", "Massachusetts"),
    ("new_hampshire", "New Hampshire"),
    ("ai", "Artificial Intelligence"),
    ("world", "World"),
]
NAV_LABELS = {"federal": "Federal", "massachusetts": "Mass.", "new_hampshire": "N.H.",
              "ai": "AI", "world": "World"}
PRIORITY_TOPICS = ["labor", "healthcare", "education"]
TOPIC_LABELS = {"labor": "Labor", "healthcare": "Health care", "education": "Education"}
TIER_ORDER = ["primary", "high", "mostly", "mixed", "low", "unrated"]
LEAN_BUCKETS = ["Left", "Center-Left", "Center", "Center-Right", "Right"]
STORY_TEXT_FIELDS = ["headline", "what_changed", "what_it_does", "who_it_affects"]

# Weekdays and months spelled out so output never depends on the machine's locale.
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


class BriefingError(Exception):
    pass


# ---------------------------------------------------------------- ratings

def load_outlets() -> tuple[dict, dict]:
    reg = json.loads(OUTLETS.read_text())
    by_domain = {}
    for o in reg["outlets"]:
        for d in o["domains"]:
            by_domain[d.lower()] = o
    return by_domain, reg["tiers"]


def match_outlet(url: str, by_domain: dict) -> dict | None:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    # try the full host, then progressively shorter parents (news.bloomberglaw.com -> bloomberglaw.com)
    for i in range(len(parts) - 1):
        cand = ".".join(parts[i:])
        if cand in by_domain:
            return by_domain[cand]
    return None


def lean_bucket(lean: str) -> str | None:
    l = lean.lower()
    if l.startswith("n/a"):
        return None
    if "far left" in l or l.startswith("left"):
        return "Left"
    if "far right" in l or l.startswith("right"):
        return "Right"
    if "center-left" in l:
        return "Center-Left"
    if "center-right" in l:
        return "Center-Right"
    if l.startswith("center"):
        return "Center"
    return None


def resolve_source(src: dict, by_domain: dict, where: str) -> dict:
    url = src.get("url", "")
    if not re.match(r"^https?://", url):
        raise BriefingError(f"{where}: source needs a full link starting with http(s)://, got {url!r}")
    outlet = match_outlet(url, by_domain)
    inline = src.get("rating")
    if outlet:
        info = dict(outlet)
    elif inline:
        for k in ("lean", "tier", "mbfc", "adfontes"):
            if k not in inline:
                raise BriefingError(f"{where}: inline rating for {url} is missing '{k}'")
        if inline["tier"] not in TIER_ORDER:
            raise BriefingError(f"{where}: rating tier must be one of {TIER_ORDER}")
        info = {"name": src.get("outlet") or urlparse(url).hostname, **inline}
    else:
        info = {"name": src.get("outlet") or urlparse(url).hostname, "lean": "Unknown",
                "tier": "unrated", "mbfc": "Not rated", "adfontes": "Not rated"}
    if src.get("outlet") and not outlet:
        info["name"] = src["outlet"]
    return {"url": url, "title": src.get("title") or info["name"], "outlet": info}


# ---------------------------------------------------------------- validate

def validate(data: dict, by_domain: dict) -> dict:
    try:
        date.fromisoformat(data["date"])
    except Exception:
        raise BriefingError("top-level 'date' must be YYYY-MM-DD")
    sections = data.get("sections")
    if not isinstance(sections, dict):
        raise BriefingError("'sections' must be an object with federal / massachusetts / new_hampshire")
    unknown = set(sections) - {k for k, _ in SECTIONS}
    if unknown:
        raise BriefingError(f"unknown section(s): {sorted(unknown)}")

    out = {"date": data["date"], "generated_at": data.get("generated_at"),
           "note": data.get("note"), "sections": {}}
    total = 0
    for key, _ in SECTIONS:
        blocks = sections.get(key, [])
        resolved_blocks, seen = [], set()
        for bi, blk in enumerate(blocks):
            topic = blk.get("topic")
            bwhere = f"{key} block {bi + 1} ({blk.get('label') or topic})"
            if topic not in PRIORITY_TOPICS + ["other"]:
                raise BriefingError(f"{bwhere}: topic must be labor, healthcare, education or other")
            if topic == "other" and not blk.get("label"):
                raise BriefingError(f"{bwhere}: topic 'other' needs a 'label' (e.g. Housing)")
            ident = (topic, (blk.get("label") or "").lower())
            if ident in seen:
                raise BriefingError(f"{bwhere}: two blocks share this topic; merge them into one")
            seen.add(ident)
            if not str(blk.get("overview", "")).strip():
                raise BriefingError(f"{bwhere}: missing 'overview' (the big-picture paragraph)")
            items = blk.get("items") or []
            if not items:
                raise BriefingError(f"{bwhere}: a block needs at least one item")
            res_items = []
            for i, s in enumerate(items):
                where = f"{bwhere} item {i + 1} ({s.get('headline', 'no headline')[:50]!r})"
                for f in STORY_TEXT_FIELDS:
                    if not str(s.get(f, "")).strip():
                        raise BriefingError(f"{where}: missing '{f}'")
                srcs = s.get("sources") or []
                if not srcs:
                    raise BriefingError(f"{where}: every item must link to at least one source")
                r = dict(s)
                r["sources"] = [resolve_source(x, by_domain, where) for x in srcs]
                res_items.append(r)
            rb = dict(blk)
            rb["items"] = res_items
            resolved_blocks.append(rb)
            total += len(res_items)
        # labor, health care, education first; otherwise keep the writer's order
        rank = {t: n for n, t in enumerate(PRIORITY_TOPICS)}
        resolved_blocks.sort(key=lambda b: rank.get(b["topic"], len(PRIORITY_TOPICS)))
        out["sections"][key] = resolved_blocks
    if total == 0:
        raise BriefingError("briefing has no stories")
    return out


def all_items(b: dict, key: str | None = None):
    for k, _ in SECTIONS:
        if key and k != key:
            continue
        for blk in b["sections"][k]:
            yield from blk["items"]


# ---------------------------------------------------------------- render

def e(s) -> str:
    return html.escape(str(s), quote=True)


def long_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{DAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}, {d.year}"


def story_trust(story: dict) -> tuple[str, list[dict]]:
    """Return (level, flagged_sources). level: 'ok' | 'caution' | 'warning'."""
    strong = any(s["outlet"]["tier"] in ("primary", "high") for s in story["sources"])
    flagged = [s for s in story["sources"] if s["outlet"]["tier"] in ("mixed", "low", "unrated")]
    if flagged:
        # weak source with no strong corroboration -> loud; corroborated -> softer note
        return ("caution" if strong else "warning"), flagged
    if not strong:  # only 'mostly reliable' outlets
        return "caution", list(story["sources"])
    return "ok", []


def rating_sentence(o: dict) -> str:
    return (f"{e(o['name'])} — lean: {e(o['lean'])}. "
            f"Media Bias/Fact Check: {e(o['mbfc'])}. Ad Fontes Media: {e(o['adfontes'])}.")


def render_trust_box(story: dict, tiers_text: dict) -> str:
    level, flagged = story_trust(story)
    if level == "ok":
        return ""
    if level == "warning":
        head = "Check the source"
        lead = ("This story is not confirmed by a highly rated outlet or an official record. "
                "The information comes from:")
    else:
        head = "Source note"
        if any(s["outlet"]["tier"] in ("mixed", "low", "unrated") for s in flagged):
            lead = ("Some details here come from an outlet with a weaker reliability rating; "
                    "the core facts are backed by a highly rated source.")
        else:
            lead = "This story comes only from outlets rated mostly (not highly) reliable:"
    items = "".join(
        f'<li><strong>{e(tiers_text.get(s["outlet"]["tier"], s["outlet"]["tier"]))}.</strong> '
        f'{rating_sentence(s["outlet"])}</li>' for s in flagged)
    extra = f'<p>{e(story["source_note"])}</p>' if story.get("source_note") else ""
    return (f'<aside class="trust {level}" role="note"><p class="trust-h">{head}</p>'
            f'<p>{lead}</p><ul>{items}</ul>{extra}</aside>')


def render_sources(story: dict, tiers_text: dict) -> str:
    rows = []
    for s in story["sources"]:
        o = s["outlet"]
        tier = o["tier"]
        rows.append(
            f'<li><a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["title"])}</a>'
            f'<span class="src-meta"><span class="outlet">{e(o["name"])}</span>'
            f'<span class="chip t-{tier}" title="{e(rating_sentence(o))}">{e(tiers_text.get(tier, tier))}</span>'
            f'<span class="lean">{e(o["lean"])}</span></span></li>')
    return f'<ul class="sources">{"".join(rows)}</ul>'


def render_item(story: dict, tiers_text: dict, anchor: str) -> str:
    status = f'<p class="status">{e(story["status"])}</p>' if story.get("status") else ""
    nxt = (f'<div class="row"><dt>What\'s next</dt><dd>{e(story["whats_next"])}</dd></div>'
           if story.get("whats_next") else "")
    return f"""
  <section class="item" id="{anchor}">
    <h4>{e(story["headline"])}</h4>
    {status}
    {render_trust_box(story, tiers_text)}
    <dl>
      <div class="row"><dt>What changed</dt><dd>{e(story["what_changed"])}</dd></div>
      <div class="row"><dt>What it does</dt><dd>{e(story["what_it_does"])}</dd></div>
      <div class="row"><dt>Who it affects</dt><dd>{e(story["who_it_affects"])}</dd></div>
      {nxt}
    </dl>
    <p class="src-h">Sources</p>
    {render_sources(story, tiers_text)}
  </section>"""


def render_block(blk: dict, tiers_text: dict, anchor: str) -> str:
    topic = blk["topic"]
    label = blk.get("label") or TOPIC_LABELS.get(topic, "Policy")
    n = len(blk["items"])
    anchors = [f"{anchor}-{i + 1}" for i in range(n)]
    toc = ""
    if n > 1:
        links = "".join(f'<li><a href="#{a}">{e(it["headline"])}</a></li>'
                        for a, it in zip(anchors, blk["items"]))
        toc = f'<ol class="toc">{links}</ol>'
    items = "".join(render_item(it, tiers_text, a) for a, it in zip(anchors, blk["items"]))
    count = f'{n} update{"s" if n != 1 else ""}'
    return f"""
<article class="block bk-{e(topic)}" id="{anchor}">
  <header class="bk-head">
    <h3>{e(label)}</h3><span class="bk-count">{count}</span>
  </header>
  <div class="overview"><p class="ov-h">The big picture</p><p>{e(blk["overview"])}</p></div>
  {toc}
  {items}
</article>"""


def spectrum(b: dict) -> str:
    counts = Counter()
    seen = set()
    for st in all_items(b):
        for s in st["sources"]:
            name = s["outlet"]["name"]
            bucket = lean_bucket(s["outlet"]["lean"])
            if bucket and name not in seen:
                seen.add(name)
                counts[bucket] += 1
    if not counts:
        return ""
    cells = "".join(
        f'<div class="sp-cell"><span class="sp-n">{counts.get(k, 0)}</span><span class="sp-l">{k}</span></div>'
        for k in LEAN_BUCKETS)
    return (f'<section class="spectrum" aria-label="Political lean of outlets cited">'
            f'<p class="sp-h">Outlets cited today, by lean</p><div class="sp-row">{cells}</div>'
            f'<p class="sp-f">Official records and agency documents are not counted.</p></section>')


CSS = """
:root{--bg:#f7f5f0;--card:#fff;--ink:#1c1b19;--muted:#5f5b53;--line:#e4dfd4;--accent:#1f4e79;
--labor:#8a4b0f;--labor-bg:#fbeedd;--health:#0d6b58;--health-bg:#dff3ec;--edu:#5a3d8a;--edu-bg:#ece5f7;
--other:#4a4a4a;--other-bg:#ececec;--warn:#8a1c1c;--warn-bg:#fdecea;--caut:#7a5a00;--caut-bg:#fff6d9;
--ok:#1d6b35;--ok-bg:#e2f3e7}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#151514;--card:#1f1f1d;--ink:#ecebe7;
--muted:#a9a59c;--line:#34332f;--accent:#8fb8e3;--labor:#f0b070;--labor-bg:#3a2a18;--health:#6fd3b8;
--health-bg:#17332b;--edu:#c3a9f0;--edu-bg:#2c2440;--other:#cfcfcf;--other-bg:#2e2e2e;--warn:#f2a3a3;
--warn-bg:#3b1d1d;--caut:#f1d27a;--caut-bg:#3a3117;--ok:#8fdba5;--ok-bg:#1b3323}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent)}
.wrap{max-width:680px;margin:0 auto;padding:0 16px 48px}
header.top{padding:28px 0 8px}
.kicker{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0}
h1{font-size:28px;line-height:1.2;margin:4px 0 2px}
.date{color:var(--muted);margin:0}
.stale{display:none;background:var(--caut-bg);color:var(--caut);border-radius:10px;padding:10px 12px;margin:14px 0 0;font-size:15px}
.note{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:16px 0 0;font-size:16px}
nav.jump{position:sticky;top:0;z-index:5;background:var(--bg);display:flex;flex-wrap:nowrap;gap:6px;padding:8px 0;scrollbar-width:none;margin-top:12px;border-bottom:1px solid var(--line);overflow-x:auto}
nav.jump a{flex:0 0 auto;text-decoration:none;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:999px;padding:4px 9px;font-size:13.5px;font-weight:600}
nav.jump a span{color:var(--muted);font-weight:500;margin-left:3px}
section.sec{scroll-margin-top:60px;padding-top:28px}
.sec-kicker{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:0 0 2px}
nav.jump::-webkit-scrollbar{display:none}
h2{font-size:22px;margin:0 0 10px;padding-bottom:6px;border-bottom:2px solid var(--ink)}
.empty{color:var(--muted);font-style:italic}
.block{--c:var(--accent);--cbg:var(--other-bg);background:var(--card);border:1px solid var(--line);border-top:5px solid var(--c);border-radius:14px;margin:0 0 18px;overflow:hidden;scroll-margin-top:60px}
.bk-labor{--c:var(--labor);--cbg:var(--labor-bg)}.bk-healthcare{--c:var(--health);--cbg:var(--health-bg)}.bk-education{--c:var(--edu);--cbg:var(--edu-bg)}
.bk-head{display:flex;align-items:baseline;justify-content:space-between;gap:10px;padding:14px 16px 0}
.bk-head h3{font-size:21px;line-height:1.25;margin:0;color:var(--c)}
.bk-count{font-size:13px;color:var(--muted);white-space:nowrap}
.overview{background:var(--cbg);margin:12px 16px 0;border-radius:10px;padding:10px 12px}
.overview p{margin:0}.ov-h{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--c);margin-bottom:2px!important}
.toc{margin:12px 16px 0;padding-left:22px;font-size:15px}.toc li{margin:0 0 4px}.toc a{color:var(--ink);text-decoration-color:var(--line)}
.item{padding:16px;border-top:1px solid var(--line);margin-top:14px;scroll-margin-top:60px}
.item h4{font-size:18px;line-height:1.3;margin:0 0 4px}
.status{font-size:13px;color:var(--muted);margin:0 0 10px}
dl{margin:0}.row{margin:0 0 10px}
dt{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
dd{margin:2px 0 0}
.trust{border-radius:10px;padding:10px 12px;margin:0 0 12px;font-size:15px}
.trust p{margin:0 0 4px}.trust ul{margin:4px 0 0;padding-left:18px}
.trust-h{font-weight:700}
.trust.warning{background:var(--warn-bg);color:var(--warn);border-left:4px solid var(--warn)}
.trust.caution{background:var(--caut-bg);color:var(--caut);border-left:4px solid var(--caut)}
.src-h{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin:12px 0 4px}
.sources{list-style:none;margin:0;padding:0}
.sources li{padding:8px 0;border-top:1px solid var(--line);font-size:15px;overflow-wrap:anywhere}
.src-meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:3px;font-size:13px;color:var(--muted)}
.outlet{font-weight:600;color:var(--ink)}
.chip{border-radius:6px;padding:1px 7px;font-weight:600}
.t-primary,.t-high{color:var(--ok);background:var(--ok-bg)}
.t-mostly{color:var(--other);background:var(--other-bg)}
.t-mixed{color:var(--caut);background:var(--caut-bg)}
.t-low,.t-unrated{color:var(--warn);background:var(--warn-bg)}
.spectrum{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:28px 0 0}
.sp-h{margin:0 0 8px;font-weight:700;font-size:15px}
.sp-row{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;text-align:center}
.sp-cell{background:var(--bg);border-radius:8px;padding:6px 2px}
.sp-n{display:block;font-size:20px;font-weight:700}.sp-l{display:block;font-size:11px;color:var(--muted)}
.sp-f{margin:8px 0 0;font-size:13px;color:var(--muted)}
footer{margin-top:28px;font-size:14px;color:var(--muted)}
footer p{margin:0 0 8px}
.archive li{margin:0 0 8px}
"""


def page(title: str, body: str, extra_head: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex">
<meta name="color-scheme" content="light dark">
<title>{e(title)}</title>
<style>{CSS}</style>
{extra_head}
</head>
<body><div class="wrap">{body}</div></body>
</html>
"""


STATES = [("massachusetts", "Massachusetts"), ("new_hampshire", "New Hampshire")]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "topic"


def display_sections(b: dict) -> list[dict]:
    """Page order: Federal, World, then topic sections (state news grouped by topic, plus AI).

    The data stays organized by government; Massachusetts and New Hampshire blocks are
    regrouped here so each topic section holds one block per state.
    """
    out = [
        {"id": "federal", "title": "Federal", "nav": "Federal", "blocks": b["sections"]["federal"],
         "empty": "Nothing of real substance at the federal level today."},
        {"id": "world", "title": "World", "nav": "World", "blocks": b["sections"]["world"],
         "empty": "Nothing of real substance internationally today."},
    ]
    topics: dict[str, dict] = {}
    for key, state in STATES:
        for blk in b["sections"][key]:
            title = blk.get("label") or TOPIC_LABELS.get(blk["topic"], "Policy")
            tid = slug(title)
            t = topics.setdefault(tid, {"id": tid, "title": title, "nav": title, "topic": blk["topic"],
                                        "kicker": "Massachusetts & New Hampshire", "blocks": []})
            t["blocks"].append({**blk, "label": state})
    rank = {t: n for n, t in enumerate(PRIORITY_TOPICS)}
    ordered = sorted(topics.values(), key=lambda t: rank.get(t["topic"], len(PRIORITY_TOPICS)))
    priority = [t for t in ordered if t["topic"] in rank]
    others = [t for t in ordered if t["topic"] not in rank]
    ai = {"id": "ai", "title": "Artificial Intelligence", "nav": "AI", "blocks": b["sections"]["ai"],
          "empty": "No major AI developments today."}
    out += priority + [ai] + others
    if not topics:
        out.append({"id": "states", "title": "Massachusetts & New Hampshire", "nav": "MA & NH",
                    "blocks": [], "empty": "No state policy news of real substance today."})
    return out


def render_briefing(b: dict, tiers_text: dict, archive_prefix: str) -> str:
    nav, secs = [], []
    for sec in display_sections(b):
        key, blocks = sec["id"], sec["blocks"]
        n = sum(len(blk["items"]) for blk in blocks)
        nav.append(f'<a href="#{key}">{e(sec["nav"])}<span>{n}</span></a>')
        inner = "".join(render_block(blk, tiers_text, f"{key}-{i + 1}")
                        for i, blk in enumerate(blocks)) or \
            f'<p class="empty">{e(sec.get("empty", "Nothing today."))}</p>'
        kicker = f'<p class="sec-kicker">{e(sec["kicker"])}</p>' if sec.get("kicker") else ""
        secs.append(f'<section class="sec" id="{key}">{kicker}<h2>{e(sec["title"])}</h2>{inner}</section>')
    note = f'<p class="note">{e(b["note"])}</p>' if b.get("note") else ""
    gen = ""
    if b.get("generated_at"):
        gen = f'<p>Compiled {e(b["generated_at"])}.</p>'
    stale_js = f"""<script>
(function(){{try{{var d="{b['date']}";var now=new Date();
var et=new Intl.DateTimeFormat('en-CA',{{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}}).format(now);
if(et>d){{var el=document.getElementById('stale');el.textContent="Heads up: this is the "+d+" briefing. Today's hasn't been published yet.";el.style.display='block';}}}}catch(e){{}}}})();
</script>"""
    body = f"""
<header class="top">
  <p class="kicker">Morning Policy Briefing</p>
  <h1>What changed, and who it affects</h1>
  <p class="date">{long_date(b["date"])}</p>
  <p class="stale" id="stale"></p>
  {note}
</header>
<nav class="jump" aria-label="Sections">{"".join(nav)}</nav>
{"".join(secs)}
{spectrum(b)}
<footer>
  <p>Reliability and lean labels summarize ratings from Media Bias/Fact Check and Ad Fontes Media.
  The weaker a source's rating, the more prominently this page flags it.</p>
  {gen}
  <p><a href="{archive_prefix}archive/index.html">Past briefings</a></p>
</footer>
{stale_js}"""
    return page(f"Policy Briefing — {long_date(b['date'])}", body)


def render_archive_index() -> str:
    days = sorted((p.stem for p in (DOCS / "archive").glob("????-??-??.html")), reverse=True)
    items = "".join(f'<li><a href="{d}.html">{long_date(d)}</a></li>' for d in days)
    body = (f'<header class="top"><p class="kicker">Morning Policy Briefing</p><h1>Past briefings</h1></header>'
            f'<ul class="archive">{items}</ul><footer><p><a href="../index.html">Latest briefing</a></p></footer>')
    return page("Past Briefings", body)


# ---------------------------------------------------------------- main

def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    args = [a for a in argv if a != "--check"]
    if args:
        path = Path(args[0])
    else:
        files = sorted(DATA.glob("????-??-??.json"))
        if not files:
            print("No briefing data found in data/", file=sys.stderr)
            return 1
        path = files[-1]
    by_domain, tiers_text = load_outlets()
    try:
        data = json.loads(path.read_text())
        b = validate(data, by_domain)
    except json.JSONDecodeError as ex:
        print(f"FAILED: {path} is not valid JSON: {ex}", file=sys.stderr)
        return 2
    except BriefingError as ex:
        print(f"FAILED: {ex}", file=sys.stderr)
        return 2

    counts = {k: sum(1 for _ in all_items(b, k)) for k, _ in SECTIONS}
    unrated = sorted({s["outlet"]["name"] for st in all_items(b)
                      for s in st["sources"] if s["outlet"]["tier"] == "unrated"})
    print(f"OK: {path.name} — {sum(counts.values())} stories {counts}")
    if unrated:
        print(f"NOTE: unrated outlets (flagged on the page): {', '.join(unrated)}")
    if check_only:
        return 0

    (DOCS / "archive").mkdir(parents=True, exist_ok=True)
    (DOCS / ".nojekyll").write_text("")
    (DOCS / "archive" / f"{b['date']}.html").write_text(render_briefing(b, tiers_text, "../"))
    # index.html always shows the newest day on record
    newest = sorted(DATA.glob("????-??-??.json"))[-1].stem
    if b["date"] >= newest:
        (DOCS / "index.html").write_text(render_briefing(b, tiers_text, ""))
    (DOCS / "archive" / "index.html").write_text(render_archive_index())
    print(f"Wrote docs/index.html and docs/archive/{b['date']}.html")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
