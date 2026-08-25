"""
daily.py — what Railway's cron actually runs.

1. If ANTHROPIC_API_KEY is set and the "scripted" backlog is running low,
   ask Scribe (pipeline/scriptwriter.py) to write more from the queued
   headlines. Skipped silently if no key is present yet — the pipeline
   still runs on whatever's already scripted.
2. Render every "scripted" video that doesn't already have an output
   file (so re-running the same day doesn't redo finished work).
3. Exit. Railway's cron restarts this fresh next time (see README).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from orchestrator import produce, ROOT, OUT

PLAN_PATH = os.path.join(ROOT, "content_plan.json")
MIN_SCRIPTED_BUFFER = 3


def top_up_backlog():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[daily] no ANTHROPIC_API_KEY set — skipping auto-ideation, using existing backlog")
        return
    with open(PLAN_PATH) as f:
        plan = json.load(f)

    scripted = [v for v in plan["backlog"] if v["status"] == "scripted"]
    queued = [v for v in plan["backlog"] if v["status"] == "queued_headline_only"]

    # Buffer depth = scripted items not yet rendered, not all-time scripted
    # count. "scripted" status never changes once set, so counting it
    # directly meant this permanently read "3 >= 3" the moment the first
    # backlog was rendered — Scribe would never fire again, key or no key.
    unrendered = [v for v in scripted if not os.path.exists(os.path.join(OUT, f"{v['id']}.mp4"))]
    if len(unrendered) >= MIN_SCRIPTED_BUFFER or not queued:
        return

    from pipeline.scriptwriter import generate_scripts, append_to_plan
    to_cover = queued[:MIN_SCRIPTED_BUFFER]
    topics = [v["title"] for v in to_cover]
    covered_ids = {v["id"] for v in to_cover}
    existing_titles = [v["title"] for v in plan["backlog"]]
    print(f"[daily] Scribe generating {len(topics)} new scripts...")
    try:
        new_scripts = generate_scripts(topics, existing_titles)
    except Exception as e:
        # Expired/revoked/rate-limited key, network blip, malformed JSON back
        # from the model — none of that should take the whole run down.
        # Render whatever's already scripted and try ideation again next tick.
        print(f"[daily] Scribe failed ({e.__class__.__name__}: {e}) — "
              f"continuing with existing backlog, will retry next run")
        return

    append_to_plan(new_scripts, PLAN_PATH)

    # Mark the source headlines consumed BY ID, not by title text — Scribe
    # usually writes a punchier title than the original headline, so a
    # text match here silently never fires and the same headlines get
    # re-sent to Scribe forever, burning API calls on duplicate coverage.
    with open(PLAN_PATH) as f:
        plan = json.load(f)
    for v in plan["backlog"]:
        if v["id"] in covered_ids and v["status"] == "queued_headline_only":
            v["status"] = "superseded"
    with open(PLAN_PATH, "w") as f:
        json.dump(plan, f, indent=2)


def render_new():
    with open(PLAN_PATH) as f:
        plan = json.load(f)
    scripted = [v for v in plan["backlog"] if v["status"] == "scripted"]
    for i, video in enumerate(scripted):
        out_path = os.path.join(OUT, f"{video['id']}.mp4")
        if os.path.exists(out_path):
            continue
        produce(video, palette_idx=i)
        # TODO once publisher credentials are set: call publishers/*.py here
        # with out_path + the matching *.metadata.json for this video.


if __name__ == "__main__":
    top_up_backlog()
    render_new()
