# Video Production Workflow

How a customer brief becomes a delivered 30-minute documentary. The code lives in
`pipeline/`; implementation detail (provider interfaces, cost drivers, assembly
internals) is in [`pipeline.md`](pipeline.md).

## 1. Brief ingestion
A customer submits a topic plus criteria through the frontend; the backend stores
it and hands the pipeline `--topic` and `--criteria`.

## 2. Research — `pipeline/research.py`
The research provider returns a structured brief: facts with dates, a timeline,
and numbered citations. Perplexity (live web search) is preferred; OpenAI is the
fallback and is marked `web_search: false` in the brief. Output:
`research_brief.json` + `research_brief.md`.

## 3. Scriptwriting — `pipeline/scriptwriter.py`
An outline call fixes the chapter arc; one call per chapter writes narrator prose
with `[VISUAL: ...]` cues every 60–90 spoken words and `[S#]` citation markers on
every factual sentence. Word count is targeted at
`TARGET_MINUTES × WORDS_PER_MINUTE` (30 × 140 ≈ 4,200 words) and the drift is
recorded in `script.json → runtime`. Output: `script.md` + `script.json`.

## 4. Fact check — `pipeline/fact_checker.py`
Deterministic audit of every factual sentence against the brief's citations.
Uncited claims and citations that do not exist in the brief block the run before
any audio or video is produced. Output: `factcheck_report.json` + `.md`.

## 5. Narration — `pipeline/narration.py`
One TTS call per chapter (ElevenLabs preferred, OpenAI TTS fallback), so a failure
re-bills one chapter instead of the whole video. Chapter audio duration is the
authoritative timing source for assembly. Output: `audio/chapter_NN.*` +
`narration.json`.

## 6. Visual assets — `pipeline/assets.py`
One image per visual cue, at 16:9, with a shared style suffix for visual
consistency. Output: `images/chNN_MMM.png` + `assets.json`.

## 7. Assembly — `pipeline/assembly.py`
Chapter audio is normalised and concatenated; each chapter's duration is split
across its cues by narrator word count; stills are encoded in batches and muxed
with the narration into an H.264/AAC MP4 at 1080p. Output: `final_video.mp4`.

## 8. Delivery
`run.json` lists every artifact, the providers used, and the fact-check verdict.
The backend marks the order complete and the video is delivered to the customer's
account.

## Offline mode
`--offline` / `PIPELINE_OFFLINE=1` swaps each provider for a deterministic stub
(including silent audio of the right duration and labelled Pillow frames) while
keeping parsing, timing, fact-check plumbing and the real ffmpeg render. Use it
for development and CI; its output is labelled not-for-publication.

## Dev loop
```bash
python -m pytest tests -q
python -m pipeline.cli providers        # which provider each stage will use
python -m pipeline.cli run --topic "..." --out /tmp/proof --offline
```
Keep renders in `/tmp`: a 30-minute 1080p MP4 plus stills will not fit in a
tight `/home` quota, and rendered video must never be committed.
