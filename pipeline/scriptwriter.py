"""
scriptwriter.py — the actual agents that replace me (Claude, in this
chat) once this runs unattended.

Two stages, matching a real content pipeline:
  - Scout:  generate_topics()  — invents brand-new headline ideas from
            scratch when the "queued_headline_only" backlog runs dry.
            Without this, the pipeline can only ever expand a fixed set
            of headlines someone seeded by hand, then permanently stall
            once they're used up.
  - Scribe: generate_scripts() — expands existing queued headlines into
            full hook/body/cta scripts, as before.

Needs ANTHROPIC_API_KEY in the environment of wherever this is deployed
(e.g. a Railway service variable) — not runnable in this dev sandbox
since no key is present here. api.anthropic.com itself IS reachable
from this sandbox's network allowlist, so once a key is added this
needs no other change to run right here too.
"""
import json
import os

SCRIBE_SYSTEM = """You write short-form personal-finance video scripts for a channel
called "Money Beats". Each script is 4-5 lines: one hook line (pattern
interrupt, must earn the next 2 seconds), 2-3 body lines (one concrete
claim each, plain numbers not vague ones), one CTA line (short, no
hard sell). Plain spoken English, no jargon, no hashtags in the script
itself. Return ONLY valid JSON: a list of {"title": str, "lines": [{"beat":
"hook"|"body"|"cta", "text": str}, ...]}."""

SCOUT_SYSTEM = """You come up with short-form video topic ideas for a personal-finance
channel called "Money Beats" — the same hook-driven style as: "Your savings
account is losing you money", "Compound interest in 40 seconds", "The credit
score myth costing you thousands". Each idea should be ONE punchy, specific,
scroll-stopping headline — a real claim or question, not a vague topic label.
Cover a mix of saving, investing, credit, debt, taxes, and everyday money
psychology. Return ONLY valid JSON: a list of plain strings, no other fields."""


def _extract_text(resp):
    text = next(block.text for block in resp.content if block.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text[4:] if text.startswith("json") else text
    return text.strip()


def generate_topics(existing_titles: list[str], n: int = 6) -> list[str]:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = (
        f"Generate {n} new headline ideas.\n"
        f"Avoid repeating or closely resembling any of these existing titles: {existing_titles}"
    )
    resp = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1000,
        system=SCOUT_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(_extract_text(resp))


def generate_scripts(topics: list[str], existing_titles: list[str]) -> list[dict]:
    import anthropic  # pip install anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = (
        f"Topics to cover: {topics}\n"
        f"Avoid repeating these already-published titles: {existing_titles}\n"
        f"Write one script per topic."
    )
    resp = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=2000,
        system=SCRIBE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(_extract_text(resp))


def append_topics_to_plan(new_topics: list[str], plan_path: str):
    with open(plan_path) as f:
        plan = json.load(f)
    next_n = len(plan["backlog"]) + 1
    for title in new_topics:
        plan["backlog"].append({
            "id": f"vid{next_n:03d}",
            "status": "queued_headline_only",
            "title": title,
        })
        next_n += 1
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)


def append_to_plan(new_scripts: list[dict], plan_path: str):
    with open(plan_path) as f:
        plan = json.load(f)
    next_n = len(plan["backlog"]) + 1
    for s in new_scripts:
        plan["backlog"].append({
            "id": f"vid{next_n:03d}",
            "status": "scripted",
            "title": s["title"],
            "lines": s["lines"],
        })
        next_n += 1
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)
