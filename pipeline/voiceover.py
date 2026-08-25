"""
voiceover.py
Turns script lines into timed audio.

DEMO ENGINE (active now): espeak-ng, fully offline, zero API key needed.
  This is what actually runs in this sandbox and is what produced the
  sample videos. Voice quality is robotic — it exists to prove the
  pipeline's timing/sync/assembly logic end to end without depending
  on any external service.

PRODUCTION ENGINE (stubbed below, not run here): swap in ElevenLabs,
  PlayHT, or OpenAI TTS by implementing `synthesize_line_prod()` and
  flipping ENGINE below. Those need an API key + real network access
  (this dev sandbox can't reach those hosts — see README).
"""
import json
import subprocess
import wave
import contextlib
import os

ENGINE = "espeak-ng"  # swap to "prod" once a real TTS key + host is wired up

VOICE = "en-us+f3"     # espeak-ng voice (female-leaning, US)
RATE = 172              # words per minute
PITCH = 48


def _wav_duration(path: str) -> float:
    with contextlib.closing(wave.open(path, 'r')) as f:
        frames = f.getnframes()
        rate = f.getframerate()
        return frames / float(rate)


def synthesize_line_espeak(text: str, out_path: str) -> float:
    subprocess.run(
        ["espeak-ng", "-v", VOICE, "-s", str(RATE), "-p", str(PITCH),
         "-g", "8",  # small gap between words, sounds less clipped
         text, "-w", out_path],
        check=True, capture_output=True
    )
    return _wav_duration(out_path)


def synthesize_line_prod(text: str, out_path: str) -> float:
    """
    Placeholder for a real neural TTS call (ElevenLabs / PlayHT / OpenAI).
    Not executed in this environment — requires an API key and a host
    that can reach the provider (this sandbox's network allowlist does
    not include TTS vendor APIs). Left here so the swap is a one-line
    change in production: ENGINE = "prod".
    """
    raise NotImplementedError(
        "Wire up your TTS provider's API here once deployed with network access + API key."
    )


def build_voiceover(lines, work_dir: str):
    """
    lines: list of {"beat": str, "text": str}
    Returns: list of {"beat","text","wav_path","duration"} and the
             path to the concatenated full voiceover wav.
    """
    os.makedirs(work_dir, exist_ok=True)
    timed = []
    for i, line in enumerate(lines):
        wav_path = os.path.join(work_dir, f"line_{i:02d}.wav")
        if ENGINE == "espeak-ng":
            dur = synthesize_line_espeak(line["text"], wav_path)
        else:
            dur = synthesize_line_prod(line["text"], wav_path)
        timed.append({**line, "wav_path": wav_path, "duration": dur})

    # concatenate all line wavs with a short silence gap between them
    concat_list = os.path.join(work_dir, "concat.txt")
    gap_path = os.path.join(work_dir, "gap.wav")
    _make_silence(gap_path, 0.28)
    with open(concat_list, "w") as f:
        for i, t in enumerate(timed):
            f.write(f"file '{os.path.abspath(t['wav_path'])}'\n")
            if i != len(timed) - 1:
                f.write(f"file '{os.path.abspath(gap_path)}'\n")

    full_wav = os.path.join(work_dir, "voiceover.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-ar", "44100", "-ac", "1", full_wav],
        check=True, capture_output=True
    )

    # recompute start offsets including gaps for caption sync
    t_cursor = 0.0
    gap_dur = _wav_duration(gap_path)
    for i, t in enumerate(timed):
        t["start"] = t_cursor
        t_cursor += t["duration"]
        if i != len(timed) - 1:
            t_cursor += gap_dur
    total_duration = t_cursor

    return timed, full_wav, total_duration


def _make_silence(path, seconds):
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r=44100:cl=mono:d={seconds}", path],
        check=True, capture_output=True
    )
