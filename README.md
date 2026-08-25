# Money Beats — autonomous shorts pipeline

## What the reference video actually showed
A creator (@matt_thecoder) built a custom multi-agent system ("Aether") for
an astronomy-facts Shorts channel ("Cosmic Scale"): named sub-agents on an
orbit-style dashboard, a scheduled production calendar (script → video →
publish, several/day), and a Discord bot ("Athena") that posts daily
performance reports — hook retention, view velocity, which titles are
"breaking out" vs. flopping — back into the team channel. It's not an
Anthropic product feature; it's their own code using an LLM for the
reasoning steps (ideation, scripting, analytics commentary) wired to
deterministic code for scheduling, rendering, and publishing.

## What's actually in this repo, tested just now, in this session
```
content_plan.json        3 fully scripted videos + 3 queued headlines
pipeline/
  voiceover.py            espeak-ng TTS -> per-line timed audio (offline, real)
  captions.py              word-level timing + karaoke caption rendering
  visuals.py                 procedural animated background (no stock assets)
  assembler.py                 frames -> ffmpeg -> final mp4
  metadata.py                   per-platform title/caption/hashtags
  scriptwriter.py                 Claude-API ideation agent (needs your key)
publishers/
  youtube_publish.py       real Data API v3 upload flow
  tiktok_publish.py         real Content Posting API flow
  instagram_publish.py       real Graph API Reels flow
orchestrator.py           runs the batch end to end
output/vid001-003.mp4     <- rendered and verified in this session
```
Ran `orchestrator.py` for all 3 scripted videos: real TTS audio, real
frame-by-frame rendering, real ffmpeg mux, 1080x1920, correct duration,
captions synced to speech. That part is genuinely done and working, not a
mockup — you have the files.

## What is NOT done, and why — read this before you expect "zero input"
**This chat can't run in the background.** I only act while you and I are
in a conversation turn. There's no cron inside this product — I can't
"go away and come back" the way the video implied. To get an unattended,
scheduled system, the code needs to live somewhere that *can* run on a
timer without me — see Deployment below. That's a one-time setup step,
not an ongoing one.

**Posting to each platform needs your own credentials, and each platform
gates it differently** (verified today, not from memory):

| Platform | What's required | Reality |
|---|---|---|
| YouTube | Google Cloud project + OAuth for your channel | Easiest. Uploads default to **private** until Google audits your project (routine for a single-owner channel, budget a few days). ~100 uploads/day quota — plenty. |
| TikTok | Developer app + Content Posting API | Strictest. Unaudited apps are **forced** to SELF_ONLY (private, max 5 accounts/24h) — no way around it server-side. Audit reviews your actual consent-screen flow. Interim honest option: auto-draft, you tap once to publish. |
| Instagram | Business/Creator account + linked FB Page + Meta App Review | 2-6 week review for `instagram_business_content_publish`. Also needs the finished video hosted at a public URL (Meta pulls it, doesn't accept uploads directly). |

None of this is a limitation of the code — the `publishers/` modules are
written against each platform's real current API. They're just untestable
from here (no network path to those hosts in this sandbox, and no
account credentials exist for them here regardless).

**Voice quality is a placeholder.** espeak-ng is robotic on purpose —
it's what could actually run offline in this dev sandbox to prove the
pipeline. `pipeline/voiceover.py` has a clean swap point
(`synthesize_line_prod`) for ElevenLabs/PlayHT/OpenAI TTS once you're on
a host with real network access and an API key.

**Ongoing ideation needs your Anthropic API key.** The 3 scripts you have
were me, right now, playing that role once. `pipeline/scriptwriter.py`
calls the real API to keep doing that daily — add `ANTHROPIC_API_KEY` and
it runs itself.

## Deployment — getting to actually "self-running"
You already run ContentKit on Railway, so the same
path applies here: push this repo to a Railway service, set it to run
`orchestrator.py` on a schedule (Railway cron), and add three env vars as
you get them: `ANTHROPIC_API_KEY`, then each platform's token once its
app/audit is approved. Say the word and I'll wire up the actual Railway
service now — I have that connector available in this chat.

## Try it yourself
```
pip install -r requirements.txt   # + apt install espeak-ng ffmpeg (or your prod TTS)
python3 orchestrator.py           # renders every "scripted" video in content_plan.json
python3 orchestrator.py vid002    # or just one
```
