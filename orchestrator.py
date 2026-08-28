import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from pipeline.voiceover import build_voiceover
from pipeline.captions import words_with_timing
from pipeline.assembler import render_video
from pipeline.metadata import build_metadata

ROOT = os.path.dirname(__file__)  # code lives here, baked into the image
# Railway sets this automatically to wherever a volume is mounted (e.g.
# /app/data) — no need to hardcode the path we told it to use. Falls back
# to ROOT when unset, so this behaves the same in local/dev runs with no
# volume attached.
DATA_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", ROOT)
OUT = os.path.join(DATA_DIR, "output")
WORK = os.path.join(ROOT, ".work")  # per-render scratch, fine to lose on restart
PLAN_PATH = os.path.join(DATA_DIR, "content_plan.json")
_SEED_PLAN_PATH = os.path.join(ROOT, "content_plan.json")


def ensure_plan_seeded():
    """First boot on a fresh/empty volume: copy the git-tracked starter
    backlog onto the volume once. Every run after that reads/writes the
    volume's copy, so Scribe's new scripts and render progress actually
    persist across deploys instead of resetting to the git baseline
    every time new code ships."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PLAN_PATH):
        shutil.copy(_SEED_PLAN_PATH, PLAN_PATH)
        print(f"[orchestrator] seeded {PLAN_PATH} from git baseline (first boot on this volume)")


def ensure_youtube_creds():
    """Write YOUTUBE_CLIENT_SECRET_JSON / YOUTUBE_TOKEN_JSON (Railway env
    vars) out to files on the persisted volume, once. Returns (None, None)
    if those vars aren't set — Herald just stays idle in that case rather
    than erroring, same as Scribe does with no ANTHROPIC_API_KEY."""
    client_secret_json = os.environ.get("YOUTUBE_CLIENT_SECRET_JSON")
    token_json = os.environ.get("YOUTUBE_TOKEN_JSON")
    if not client_secret_json or not token_json:
        return None, None

    os.makedirs(DATA_DIR, exist_ok=True)
    client_secret_path = os.path.join(DATA_DIR, "client_secret.json")
    token_path = os.path.join(DATA_DIR, "token.json")
    if not os.path.exists(client_secret_path):
        with open(client_secret_path, "w") as f:
            f.write(client_secret_json)
    if not os.path.exists(token_path):
        with open(token_path, "w") as f:
            f.write(token_json)
    return client_secret_path, token_path


def produce(video, palette_idx=0):
    t0 = time.time()
    work_dir = os.path.join(WORK, video["id"])
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    print(f"[{video['id']}] writing voiceover...")
    timed_lines, voiceover_wav, duration = build_voiceover(video["lines"], work_dir)
    print(f"[{video['id']}] voiceover done: {duration:.1f}s audio")

    word_stream = words_with_timing(timed_lines)

    out_path = os.path.join(OUT, f"{video['id']}.mp4")
    print(f"[{video['id']}] rendering frames + encoding...")
    render_video(timed_lines, word_stream, voiceover_wav, duration, out_path, palette_idx)

    meta = build_metadata(video)
    meta_path = os.path.join(OUT, f"{video['id']}.metadata.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    dt = time.time() - t0
    print(f"[{video['id']}] DONE in {dt:.1f}s -> {out_path}")
    return out_path, meta_path


if __name__ == "__main__":
    ensure_plan_seeded()
    with open(PLAN_PATH) as f:
        plan = json.load(f)

    scripted = [v for v in plan["backlog"] if v["status"] == "scripted"]
    ids_to_run = sys.argv[1:] or [v["id"] for v in scripted]

    for i, video in enumerate(scripted):
        if video["id"] not in ids_to_run:
            continue
        produce(video, palette_idx=i)
