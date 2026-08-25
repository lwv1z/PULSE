import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from pipeline.voiceover import build_voiceover
from pipeline.captions import words_with_timing
from pipeline.assembler import render_video
from pipeline.metadata import build_metadata

ROOT = os.path.dirname(__file__)
WORK = os.path.join(ROOT, "work")
OUT = os.path.join(ROOT, "output")


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
    with open(os.path.join(ROOT, "content_plan.json")) as f:
        plan = json.load(f)

    scripted = [v for v in plan["backlog"] if v["status"] == "scripted"]
    ids_to_run = sys.argv[1:] or [v["id"] for v in scripted]

    for i, video in enumerate(scripted):
        if video["id"] not in ids_to_run:
            continue
        produce(video, palette_idx=i)
