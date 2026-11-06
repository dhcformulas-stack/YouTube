# Chronicle Forge

Subscription service that produces a fully researched, fact-checked 30-minute
documentary video from a customer's topic brief — script, narration, visuals and
a ready-to-upload YouTube MP4.

## Repository layout

| Path | Contents |
| --- | --- |
| `pipeline/` | Python video production pipeline (research → script → fact-check → narration → images → assembly) |
| `backend/` | Node.js/Express API, Stripe subscriptions, orders |
| `frontend/` | Next.js customer app (dashboard, pricing, checkout) |
| `docs/` | `pipeline.md` (how the video pipeline works), `workflow.md` (team process) |
| `templates/` | Markdown templates for research briefs and scripts |

## Producing a video

```bash
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
apt-get install -y ffmpeg          # or: pip install imageio-ffmpeg

# No API keys needed — deterministic stubs, real MP4:
python -m pipeline.cli run --topic "The Antikythera Mechanism" --out /tmp/proof --offline

# Production run (needs keys, see .env.example):
export OPENAI_API_KEY=...  PERPLEXITY_API_KEY=...  ELEVENLABS_API_KEY=...
python -m pipeline.cli run --topic "The Antikythera Mechanism" --out /tmp/proof
```

`<out>/run.json` is the run manifest: providers used, word count, estimated
runtime, fact-check verdict, and the path of every artifact including
`final_video.mp4`.

Which key enables which stage:

| Env var | Enables |
| --- | --- |
| `PERPLEXITY_API_KEY` | research with live web citations (preferred) |
| `OPENAI_API_KEY` | script generation, image generation, TTS fallback, research fallback |
| `ELEVENLABS_API_KEY` | narration (preferred over OpenAI TTS) |

All keys are optional in offline mode. Full details — provider order, offline
behaviour, fact-check rules, assembly internals and per-video cost drivers — are
in [`docs/pipeline.md`](docs/pipeline.md).

## Tests

```bash
python -m pytest tests -q
```
