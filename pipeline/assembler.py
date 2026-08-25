import os
import subprocess
from .visuals import render_background, W, H
from .captions import draw_captions

FPS = 24


def render_video(timed_lines, word_stream, voiceover_wav, total_duration,
                  out_path, palette_idx=0):
    n_frames = int(total_duration * FPS) + FPS  # small tail so last word holds
    ffmpeg = subprocess.Popen(
        [
            "ffmpeg", "-y",
            "-f", "rawvideo", "-pixel_format", "rgb24",
            "-video_size", f"{W}x{H}", "-framerate", str(FPS),
            "-i", "-",
            "-i", voiceover_wav,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-shortest",
            "-movflags", "+faststart",
            out_path,
        ],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )

    try:
        for f in range(n_frames):
            t = f / FPS
            frame = render_background(t, total_duration, palette_idx)
            frame = draw_captions(frame, word_stream, min(t, total_duration - 0.01))
            ffmpeg.stdin.write(frame.tobytes())
    finally:
        ffmpeg.stdin.close()
        err = ffmpeg.stderr.read().decode(errors="ignore")
        ret = ffmpeg.wait()
        if ret != 0:
            raise RuntimeError(f"ffmpeg failed ({ret}):\n{err[-3000:]}")

    return out_path
