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
    if len(scripted) >= MIN_SCRIPTED_BUFFER or not queued:
        return

    from pipeline.scriptwriter import generate_scripts, append_to_plan
    topics = [v["title"] for v in queued[:MIN_SCRIPTED_BUFFER]]
    existing_titles = [v["title"] for v in plan["backlog"]]
    print(f"[daily] Scribe generating {len(topics)} new scripts...")
    new_scripts = generate_scripts(topics, existing_titles)
    append_to_plan(new_scripts, PLAN_PATH)

    # mark the source headlines consumed so they aren't regenerated forever
    with open(PLAN_PATH) as f:
        plan = json.load(f)
    covered = {s["title"] for s in new_scripts}
    for v in plan["backlog"]:
        if v["title"] in covered and v["status"] == "queued_headline_only":
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
