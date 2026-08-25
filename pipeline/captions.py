"""
captions.py
Builds word-level timestamps from each line's known audio duration
(proportional to character length — a reasonable approximation without
a forced-aligner) and draws bold, TikTok-style word-group captions with
a highlighted current word, matching the "instant hook" lesson learned
from the reference video's own analytics report (first-line hook needs
to hit hard, so it renders slightly larger).
"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

WORDS_PER_GROUP = 3
HIGHLIGHT = (120, 240, 170)
WHITE = (255, 255, 255)
SHADOW = (0, 0, 0)


def words_with_timing(timed_lines):
    """timed_lines: output of voiceover.build_voiceover (has start/duration/text).
    Returns flat list of {"word","start","end","beat","line_index"}.
    """
    out = []
    for li, line in enumerate(timed_lines):
        words = line["text"].split()
        total_chars = sum(len(w) for w in words) or 1
        cursor = line["start"]
        for w in words:
            share = len(w) / total_chars
            dur = max(line["duration"] * share, 0.12)
            out.append({
                "word": w, "start": cursor, "end": cursor + dur,
                "beat": line["beat"], "line_index": li
            })
            cursor += dur
    return out


def _font(size):
    return ImageFont.truetype(FONT_BOLD, size)


def draw_captions(frame: Image.Image, word_stream, t: float) -> Image.Image:
    # find active word
    active_i = None
    for i, w in enumerate(word_stream):
        if w["start"] <= t < w["end"]:
            active_i = i
            break
    if active_i is None:
        # between lines / before start / after end — hold nearest group
        for i, w in enumerate(word_stream):
            if t < w["start"]:
                active_i = max(i - 1, 0)
                break
        if active_i is None:
            active_i = len(word_stream) - 1

    is_hook = word_stream[active_i]["beat"] == "hook"
    group_start = (active_i // WORDS_PER_GROUP) * WORDS_PER_GROUP
    group = word_stream[group_start:group_start + WORDS_PER_GROUP]

    size = 92 if is_hook else 78
    font = _font(size)
    draw = ImageDraw.Draw(frame)

    # measure lines, wrap to width with margin
    margin = 90
    max_w = W - margin * 2
    spacer = " "
    line_words, cur_w = [], 0
    lines = []
    for w in group:
        wbox = draw.textbbox((0, 0), w["word"] + spacer, font=font)
        ww = wbox[2] - wbox[0]
        if cur_w + ww > max_w and line_words:
            lines.append(line_words)
            line_words, cur_w = [], 0
        line_words.append(w)
        cur_w += ww
    if line_words:
        lines.append(line_words)

    line_h = size + 26
    total_h = line_h * len(lines)
    y = H * 0.62 - total_h / 2  # lower-middle third, safe from UI overlays

    for row in lines:
        row_text_w = sum(
            draw.textbbox((0, 0), w["word"] + spacer, font=font)[2] for w in row
        )
        x = (W - row_text_w) / 2
        for w in row:
            color = HIGHLIGHT if w is word_stream[active_i] else WHITE
            txt = w["word"]
            # simple outline for legibility over any background
            for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2)]:
                draw.text((x + dx, y + dy), txt, font=font, fill=SHADOW)
            draw.text((x, y), txt, font=font, fill=color)
            x += draw.textbbox((0, 0), txt + spacer, font=font)[2]
        y += line_h

    return frame
