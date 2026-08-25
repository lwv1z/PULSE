HASHTAGS_BASE = ["personalfinance", "moneytips", "financialfreedom"]


def build_metadata(video):
    title = video["title"]
    hook = next((l["text"] for l in video["lines"] if l["beat"] == "hook"), title)

    yt_title = f"{title} #shorts"
    tiktok_caption = f"{hook} {' '.join('#' + h for h in HASHTAGS_BASE)} #fyp"
    ig_caption = f"{hook}\n.\n.\n{' '.join('#' + h for h in HASHTAGS_BASE)} #reels"

    return {
        "id": video["id"],
        "youtube": {"title": yt_title[:100], "description": hook, "tags": HASHTAGS_BASE},
        "tiktok": {"caption": tiktok_caption[:150]},
        "instagram": {"caption": ig_caption},
    }
