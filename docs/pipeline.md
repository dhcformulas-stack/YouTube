# Video Production Pipeline

This is the code that produces every customer video. One CLI run turns a topic
into a finished, narration-synced H.264 MP4 plus the research, script and
fact-check artifacts that justify it.

```
research ──▶ script ──▶ fact-check ──▶ narration ──▶ images ──▶ assembly
 (LLM +      (LLM,      (deterministic  (TTS, one     (text-to-  (ffmpeg,
  web)       chaptered)  citation audit)  file/chapter)  image)     H.264 + AAC)
```

Each stage sits behind a small interface in `pipeline/providers/`, selected from
environment variables. Every stage also has a deterministic offline stub, so the
full chain — including a real render — runs with **no API keys** in dev and CI.

## Quickstart (no keys needed)

```bash
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
# ffmpeg: apt-get install -y ffmpeg   (or: pip install imageio-ffmpeg, set FFMPEG_BIN)

python -m pipeline.cli run --topic "The Antikythera Mechanism" --out /tmp/proof --offline
```

Outputs land in `--out` (keep it on `/tmp` on small disks — a 30-minute 1080p
render is ~15–40 MB plus stills):

| File | Contents |
| --- | --- |
| `run.json` | manifest: providers used, per-stage stats, timings, output paths, `publishable` flag |
| `research_brief.json` / `.md` | facts (with dates) and citations |
| `script.md` / `script.json` | chaptered script with `[VISUAL: ...]` cues and `[S#]` citation markers |
| `factcheck_report.json` / `.md` | every claim, its status, and the reason for any flag |
| `narration.json`, `audio/chapter_NN.*` | per-chapter audio |
| `assets.json`, `images/chNN_MMM.png` | one still per visual cue |
| `final_video.mp4` | the deliverable |
| `narration_full.wav` | chapter audio concatenated (intermediate) |

Offline output is labelled `OFFLINE PLACEHOLDER — NOT FOR PUBLICATION` and the
manifest carries `"publishable": false`.

## Offline mode

`--offline` or `PIPELINE_OFFLINE=1`:

| Stage | Offline behaviour |
| --- | --- |
| research | deterministic placeholder facts, citations marked `placeholder` with no URL |
| script | deterministic chaptered text with real `[VISUAL: ...]` cues and `[S#]` markers |
| narration | **silent** audio of the correct duration (words ÷ WPM), via ffmpeg |
| images | Pillow frames at the output resolution, labelled with the cue text |
| assembly | identical to production: real H.264/AAC MP4 |

The point of offline mode is that the *pipeline mechanics* — parsing, timing,
sync, encode, fact-check plumbing — are exercised for real. It is not a
substitute for a production run, and its output must never be delivered.

## Live providers and keys

Selection order per stage (first available wins, and the fallback is recorded in
`run.json` under `providers.notes`):

| Stage | 1st choice | 2nd choice | Env var that unlocks it |
| --- | --- | --- | --- |
| research | Perplexity `sonar-pro` (live web search, returns citations) | OpenAI chat (no web search) | `PERPLEXITY_API_KEY`, then `OPENAI_API_KEY` |
| script | OpenAI, one call per chapter | — | `OPENAI_API_KEY` |
| narration | ElevenLabs TTS | OpenAI TTS | `ELEVENLABS_API_KEY`, then `OPENAI_API_KEY` |
| images | OpenAI Images (`gpt-image-1` by default) | — | `OPENAI_API_KEY` |

In online mode, if no key for a stage is present the run **fails loudly**
(`ProviderUnavailable`) instead of falling back to stubs: a stub video must
never be mistaken for a deliverable. Model names, voice ids, image size and
video parameters are all env-configurable — see `.env.example`.

Two caveats worth knowing:

* The OpenAI **research** fallback has no live browsing, so its citations come
  from the model. The brief records `web_search: false` and the fact-check
  report reflects it. Perplexity is the intended research provider.
* An empty citation URL is never accepted silently: such a source is listed in
  `factcheck_report.json` → `invalid_citations`.

## Fact checking

`pipeline/fact_checker.py` is deterministic (no LLM, so it is reproducible and
free). Rules:

* a factual sentence carrying `[S3]` is **supported** when `S3` exists in the brief;
* a factual sentence with no marker is **unsupported** — "no citation";
* a marker pointing at a source not in the brief is **unsupported** — that is how
  a fabricated source is caught;
* a resolved source with no URL is **review** (flagged, does not block).

A factual sentence is detected by citation markers or by factual signals — years,
percentages, measurements, and verbs like *invented / founded / discovered /
born / died / published*.

`run` stops before narration and assembly when any **unsupported** claim exists,
so an inaccurate script cannot be rendered by accident. Override with
`--allow-factcheck-failures` only for diagnosis.

## Assembly

`pipeline/assembly.py` shells out to ffmpeg (no moviepy):

1. each chapter's audio is normalised to 44.1 kHz PCM and concatenated;
2. each chapter's audio duration is split across its cues in proportion to the
   number of narrator words under each cue — a shot stays up as long as the
   narration it illustrates (minimum `MIN_SCENE_SECONDS`);
3. stills are encoded in batches of `VIDEO_BATCH_SIZE` and the batches are
   concatenated with a stream copy, then narration is muxed in.

Batching is not cosmetic: a single filter graph over hundreds of decoded 1080p
frames gets OOM-killed on a 4 GB host. Batching keeps peak memory flat as
runtime grows.

ffmpeg resolution order: `FFMPEG_BIN` → `ffmpeg` on `PATH` → the static binary
from `imageio-ffmpeg`. Install with `apt-get install -y ffmpeg` where you have
root; on hosts where you don't, `pip install imageio-ffmpeg` is enough to render.

## Cost drivers (per video)

Cost scales with runtime and cue count; these are the quantities to watch. Stated
qualitatively on purpose — no price numbers are asserted here, because vendor
pricing changes and the owner should read it from the vendor's own pricing page
at purchase time.

| Driver | Roughly what a 30-minute video consumes |
| --- | --- |
| Research tokens | one large response (20–40 facts with sources) per video; Perplexity bills per request plus tokens, and its per-request fee dominates |
| Script tokens | ~4,200–4,600 output words ≈ 6–7k tokens **plus** the brief re-sent in every per-chapter call — 8 chapters means 8 input passes, so input tokens, not output, are the bulk |
| TTS characters | ~4,500 words ≈ 26–30k characters. ElevenLabs bills characters against the plan quota; OpenAI TTS bills per character too |
| Images | one image per cue — plan for 40–70 images at 30 minutes. This is usually the **largest** single line item |
| Compute | ffmpeg encode is local CPU only, no per-video cost |

Practical levers: fewer, longer cues (image count), a shorter runtime
(`--minutes`), a cheaper script model, and re-running a single stage instead of
the whole chain by reusing the artifacts in `--out`.

## Tests

```bash
python -m pytest tests -q
```

Covers provider selection and fallback (including the no-key failure path),
offline brief labelling, `[VISUAL: ...]` and `[S#]` parsing, fact-check flagging
of uncited and unknown-source claims, scene-duration math, and a full offline
render that ffprobe confirms is a playable 640×360 H.264 MP4.

## Adding a provider

Subclass the interface in `pipeline/providers/base.py` (`ResearchProvider`,
`ScriptProvider`, `NarrationProvider`, `ImageProvider`), implement the one
required method, then add it to the preference order and `__all__` in
`pipeline/providers/__init__.py`. Nothing else changes — `run.json` reports the
provider name automatically.
