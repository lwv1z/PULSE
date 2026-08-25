"""
scriptwriter.py — the actual "agent" that replaces me (Claude, in this
chat) once this runs unattended. Reads the current backlog + a rolling
performance summary, asks Claude for N new scripts, appends them to
content_plan.json in the same schema orchestrator.py already consumes.

Needs ANTHROPIC_API_KEY in the environment of wherever this is deployed
(e.g. a Railway service variable) — not runnable in this dev sandbox
since no key is present here. api.anthropic.com itself IS reachable
from this sandbox's network allowlist, so once a key is added this
needs no other change to run right here too.
"""
import json
import os

SYSTEM = """You write short-form personal-finance video scripts for a channel
called "Money Beats". Each script is 4-5 lines: one hook line (pattern
interrupt, must earn the next 2 seconds), 2-3 body lines (one concrete
claim each, plain numbers not vague ones), one CTA line (short, no
hard sell). Plain spoken English, no jargon, no hashtags in the script
itself. Return ONLY valid JSON: a list of {"title": str, "lines": [{"beat":
"hook"|"body"|"cta", "text": str}, ...]}."""


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
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    return json.loads(text)


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
