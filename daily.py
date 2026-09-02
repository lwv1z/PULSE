"""
daily.py — what Railway's cron actually runs.

1. Seed content_plan.json onto the persistent volume if this is the
   volume's first boot (see orchestrator.ensure_plan_seeded).
2. If ANTHROPIC_API_KEY is set and the render-ready buffer is running low:
   if the queue of raw headline ideas is empty, ask Scout to invent new
   ones from scratch first, then ask Scribe (pipeline/scriptwriter.py)
   to expand queued headlines into full scripts. Skipped silently if no
   key is present — the pipeline still runs on whatever's already scripted.
3. Render every "scripted" video that doesn't already have an output
   file (so re-running the same day doesn't redo finished work).
4. If YOUTUBE_CLIENT_SECRET_JSON / YOUTUBE_TOKEN_JSON are set, publish
   every rendered video that hasn't been uploaded yet. Skipped silently
   if unset — same graceful-idle pattern as Scribe.
5. Exit. Railway's cron restarts this fresh next time (see README).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from orchestrator import produce, ensure_plan_seeded, ensure_youtube_creds, PLAN_PATH, OUT

MIN_SCRIPTED_BUFFER = 3


def top_up_backlog():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[daily] no ANTHROPIC_API_KEY set — skipping auto-ideation, using existing backlog")
        return
    with open(PLAN_PATH) as f:
        plan = json.load(f)

    scripted = [v for v in plan["backlog"] if v["status"] == "scripted"]
    queued = [v for v in plan["backlog"] if v["status"] == "queued_headline_only"]

    unrendered = [v for v in scripted if not os.path.exists(os.path.join(OUT, f"{v['id']}.mp4"))]
    if len(unrendered) >= MIN_SCRIPTED_BUFFER:
        return

    from pipeline.scriptwriter import generate_scripts, generate_topics, append_to_plan, append_topics_to_plan

    if not queued:
        existing_titles = [v["title"] for v in plan["backlog"]]
        print("[daily] queue empty — Scout generating new topic ideas...")
        try:
            new_topics = generate_topics(existing_titles, n=MIN_SCRIPTED_BUFFER * 2)
        except Exception as e:
            print(f"[daily] Scout failed ({e.__class__.__name__}: {e}) — will retry next run")
            return
        append_topics_to_plan(new_topics, PLAN_PATH)
        with open(PLAN_PATH) as f:
            plan = json.load(f)
        queued = [v for v in plan["backlog"] if v["status"] == "queued_headline_only"]
        if not queued:
            return

    to_cover = queued[:MIN_SCRIPTED_BUFFER]
    topics = [v["title"] for v in to_cover]
    covered_ids = {v["id"] for v in to_cover}
    existing_titles = [v["title"] for v in plan["backlog"]]
    print(f"[daily] Scribe generating {len(topics)} new scripts...")
    try:
        new_scripts = generate_scripts(topics, existing_titles)
    except Exception as e:
        print(f"[daily] Scribe failed ({e.__class__.__name__}: {e}) — "
              f"continuing with existing backlog, will retry next run")
        return

    append_to_plan(new_scripts, PLAN_PATH)

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


def publish_new():
    client_secret_path, token_path = ensure_youtube_creds()
    if not client_secret_path:
        print("[daily] Herald idle — no YouTube credentials set")
        return

    from publishers.youtube_publish import upload_short

    with open(PLAN_PATH) as f:
        plan = json.load(f)

    changed = False
    for video in plan["backlog"]:
        if video["status"] != "scripted" or video.get("youtube_video_id"):
            continue
        out_path = os.path.join(OUT, f"{video['id']}.mp4")
        meta_path = os.path.join(OUT, f"{video['id']}.metadata.json")
        if not os.path.exists(out_path) or not os.path.exists(meta_path):
            continue

        with open(meta_path) as f:
            yt_meta = json.load(f)["youtube"]

        print(f"[daily] Herald uploading {video['id']}...")
        try:
            # Google's compliance audit cleared Aug 31 2026 — public uploads
            # are no longer restricted. Videos uploaded before that date are
            # still private on YouTube and need flipping by hand or via a
            # one-off cleanup; everything from here on posts public directly.
            result = upload_short(
                out_path, yt_meta["title"], yt_meta["description"], yt_meta["tags"],
                privacy_status="public",
                client_secret_path=client_secret_path, token_path=token_path,
            )
        except Exception as e:
            print(f"[daily] Herald failed on {video['id']} ({e.__class__.__name__}: {e}) — will retry next run")
            continue

        video["youtube_video_id"] = result["id"]
        changed = True
        print(f"[daily] Herald published {video['id']} -> https://youtu.be/{result['id']} (public)")

    if changed:
        with open(PLAN_PATH, "w") as f:
            json.dump(plan, f, indent=2)


def flip_legacy_private_to_public():
    """One-time cleanup: videos uploaded before Google's compliance audit
    cleared (Aug 31 2026) were forced private and stayed that way. This
    flips each of them to public exactly once, then marks it done so it
    isn't re-checked on every future run."""
    client_secret_path, token_path = ensure_youtube_creds()
    if not client_secret_path:
        return

    from publishers.youtube_publish import set_public

    with open(PLAN_PATH) as f:
        plan = json.load(f)

    changed = False
    for video in plan["backlog"]:
        vid_id = video.get("youtube_video_id")
        if not vid_id or video.get("youtube_public"):
            continue
        try:
            set_public(vid_id, client_secret_path, token_path)
            video["youtube_public"] = True
            changed = True
            print(f"[daily] Herald flipped {video['id']} ({vid_id}) to public")
        except Exception as e:
            print(f"[daily] Herald failed to flip {video['id']} public ({e.__class__.__name__}: {e}) — will retry next run")

    if changed:
        with open(PLAN_PATH, "w") as f:
            json.dump(plan, f, indent=2)


if __name__ == "__main__":
    ensure_plan_seeded()
    top_up_backlog()
    render_new()
    publish_new()
    flip_legacy_private_to_public()
