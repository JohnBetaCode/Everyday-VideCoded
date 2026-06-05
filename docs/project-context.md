# Project Context

This file is the single source of truth for the project's current state. Update it as features are added, decisions are made, or direction changes. Read it at the start of every session.

---

## Overview

**everyday2** is a "face every day" maker — a web GUI that lets you load a folder (or many folders) of daily self-portrait photos, browse them sorted by date, and see statistics about how consistently photos were taken over time. The end goal is to produce a timelapse-style video showing personal change over months and years, with automatic face detection and alignment applied before exporting. It is a full rebuild of [Face-every-day-maker](https://github.com/JohnBetaCode/Face-every-day-maker) — same idea, better implementation.

---

## Goals

- [x] Web GUI to load one or multiple image folders
- [x] Read and sort all images by date (EXIF → file mtime fallback)
- [x] Navigate through images with prev/next buttons and a slider
- [x] Show date range, days covered, and missing days per year
- [x] Detect and skip corrupted images gracefully
- [x] Face alignment (MediaPipe iris landmarks → rotation + translation)
- [x] Face zoom (normalise face size across frames by inter-ocular distance)
- [x] Side-by-side view: original image + processed result
- [x] Batch export of processed images with original filenames and dates
- [x] Date stamp (capture date) overlaid on every exported frame
- [x] Timelapse video export via ffmpeg
- [x] Filename-based date parsing as a third fallback (WP_/WIN_/YYYYMMDD patterns)
- [x] Export frame size normalisation (EXPORT_WIDTH/HEIGHT, cover-crop at read time)
- [x] Debug export mode (green diagnostic overlay with all date metadata)

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Language | Python 3.12 | |
| GUI | Streamlit ≥ 1.35 | Web app, runs locally |
| Image I/O | Pillow ≥ 10.0 | EXIF reading, display |
| CV pipeline | `src/pipeline.py` | Cascade of togglable operations |
| Background segmentation | rembg ≥ 0.1.36 + U2Net | GPU via onnxruntime-gpu, CPU fallback |
| Face alignment | MediaPipe Face Mesh ≥ 0.10 | Iris landmarks (468/473), CPU |
| Config | python-dotenv | Loads `configs/.env` at startup |
| Container | Docker + VS Code Dev Container | Base image: `nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04` |
| Container user | `ada` | Non-root for safer dev |
| GPU | nvidia-container-toolkit | Optional; remove `deploy` block if no NVIDIA GPU |
| Face detection | _TBD_ | dlib or MediaPipe, not started yet |
| Video export | ffmpeg (system) | concat demuxer; invoked via subprocess |

---

## Architecture

Single-process Streamlit app. No separate backend — all image scanning, stats, and CV operations run in-process.

```
src/
├── app.py        ← Streamlit entry point  (streamlit run src/app.py)
├── scanner.py    ← Folder scanning, EXIF extraction, stats
├── pipeline.py   ← CV operation registry and cascade runner
└── __init__.py

configs/
├── .env          ← Local dev overrides (gitignored)
└── .env.example  ← Committed template

docs/
├── project-context.md   ← This file
├── usage.md             ← Full usage guide
├── troubleshooting.md   ← Common issues and fixes
└── session-log.md       ← Auto-updated by post-commit hook
```

---

## Current Features

- Dev container (Python 3.12, Docker, VS Code) with optional NVIDIA GPU passthrough
- Automatic session log via `post-commit` git hook → `docs/session-log.md`
- `configs/.env` loaded at startup — set `DEFAULT_PHOTOS_PATH` for dev convenience
- Web GUI (`src/app.py`) with:
  - Device picker (USB/HDD auto-detection via `/media`, `/run/media`, `/proc/mounts`)
  - Multi-folder path input (one per line, recursive scan, duplicates deduplicated)
  - Images sorted newest → oldest by EXIF date (mtime fallback); EXIF auto-rotation applied
  - Prev/Next buttons + full-range slider for navigation
  - Filename, date, and position counter shown per image
  - Sidebar: compact stats table, per-year breakdown with coverage % and progress bar
  - Corrupted image detection — skipped with a warning count
- CV pipeline (`src/pipeline.py`):
  - Side-by-side view: original (left) | processed (right)
  - Operations toggled via checkboxes in sidebar, applied in cascade order
  - Each op with tunable params exposes live sliders seeded from env vars
  - Op 1 · Grayscale
  - Op 2 · Blur background (rembg U2Net segmentation + Gaussian blur, GPU-accelerated; radius via `BLUR_RADIUS`)
  - Op 3 · Align face (MediaPipe iris landmarks → rotation + translation; target position via `FACE_ALIGN_X` / `FACE_ALIGN_Y`)
  - Op 4 · Zoom face (scale to normalise inter-ocular distance; ratio via `FACE_ZOOM_RATIO`)
  - `FaceNotFoundError` raised when no face detected — warning shown, processed frame left empty
  - When multiple faces detected, largest by landmark bounding box is used
  - Pipeline runs with a spinner in the processed panel while computing
- Batch export (`⬇ Export all` button in sidebar):
  - Runs all loaded images concurrently via `ThreadPoolExecutor` (`EXPORT_WORKERS`, default 10)
  - Saves to `EXPORT_PATH/images/<source_folder>/` — grouped by source folder name
  - Frames named `frame_0001.ext`, `frame_0002.ext` … (zero-padded per folder)
  - Sort order (frame numbering) selectable in GUI: Filename A→Z / Date created / Date modified; default from `EXPORT_SORT` env var
  - Preserves EXIF bytes and sets file mtime to original photo date
  - Images with no face detected are skipped, not exported
  - Progress bar shows `N / total (%)`
  - Each frame stamped with capture date at top centre (`_draw_date`); configurable via `DATE_*` env vars
  - **Frame size normalisation**: at read time, every image is cover-scaled and center-cropped to `EXPORT_WIDTH×EXPORT_HEIGHT`; falls back to first image's post-rotation dimensions if env vars not set; same crop applied in the live GUI preview so displayed form factor matches export
  - **Filename date parsing** (sort=name): date parsed from filename before EXIF/mtime fallback; patterns: `WP_YYYYMMDD_HH_MM_SS_*`, `WIN_YYYYMMDD_HHMMSS`, plain `YYYYMMDD`
  - **Debug export mode** (`EXPORT_DEBUG=1` or sidebar checkbox): replaces date stamp with green diagnostic overlay showing all EXIF dates, filesystem timestamps, filename-parsed date, and active sort mode
- Video creation (`🎬 Create video` button in sidebar):
  - Builds one video per subfolder in `EXPORT_PATH/images/`; frames sorted A→Z by filename (`frame_0001`, `frame_0002` …)
  - Merges all per-folder videos into `EXPORT_PATH/VIDEO_NAME.VIDEO_EXTENSION` via ffmpeg concat stream copy
  - Existing videos overwritten silently (`-y` flag)
  - Configurable via `VIDEO_NAME`, `VIDEO_EXTENSION`, `VIDEO_FPS`, `VIDEO_CODEC`, `VIDEO_WIDTH`, `VIDEO_HEIGHT`
  - Output scaled to `VIDEO_WIDTH×VIDEO_HEIGHT` (default 1920×1080) via ffmpeg `scale+pad` filter; even dimensions enforced for h264
  - Shows warning if export folder has no subfolders; ffmpeg stderr truncated and surfaced on failure
- Session management:
  - Browse "Select" replaces the text area (not appends) to prevent accidental path accumulation
  - After a successful load, text area resets to exactly the scanned paths; shows message if previous session was replaced

---

## In Progress

Nothing currently in progress.

---

## Backlog

- Filter images by year or custom date range in the GUI
- Thumbnail strip / calendar heatmap view
- Async/cached folder scanning for large collections

---

## Known Issues / Constraints

- Very large folders may feel slow to scan (no async/caching yet).
- Streamlit's file input doesn't support native OS folder picker; folder path must be typed/pasted.
- Blur background (~1–3s/image on CPU, ~0.3s on GPU) — not suitable for fast browsing; best applied selectively.
- rembg U2Net model (~170 MB) downloaded on first use; stored in `u2net-cache` Docker volume.

---

## Key Decisions

| Date | Decision | Reason |
|------|----------|--------|
| 2026-05-25 | Streamlit for GUI | Fastest path to a working web UI in pure Python; easy to iterate |
| 2026-05-25 | EXIF → mtime date fallback | Most phone/camera photos have EXIF; mtime catches the rest without extra deps |
| 2026-05-25 | `img.load()` for corruption check | Forces full pixel decode — catches truncated/corrupted files that open() alone would miss |
| 2026-05-25 | Missing days = full calendar year − unique days with images | Most intuitive stat: "in 2025 you have 165 days with no photo" |
| 2026-05-25 | `python:3.12-slim` base image | Keeps image size small |
| 2026-05-25 | Non-root user `ada` in container | Safer dev environment |
| 2026-05-25 | Auto session log via `post-commit` + Claude CLI | Keep a living record of work without manual effort |
| 2026-05-27 | rembg over MediaPipe for background segmentation | Better mask quality on varied selfie backgrounds; GPU support via onnxruntime |
| 2026-05-27 | Blur background instead of remove | Keeps visual context; portrait/bokeh effect more useful than transparent cutout |
| 2026-05-27 | Named Docker volume for U2Net model cache | Avoids re-downloading 170 MB model on every container rebuild |
| 2026-05-28 | CUDA base image (`nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04`) | `python:3.12-slim` lacks CUDA libs needed by onnxruntime-gpu |
| 2026-05-28 | Python venv at `/opt/venv` | Avoids pip conflicts with apt-managed distutils packages in the CUDA image |
| 2026-05-28 | MediaPipe Tasks API over dlib for face alignment | `mp.solutions` not available on Python 3.12 / mediapipe 0.10+; Tasks API works and has iris landmarks |
| 2026-05-28 | Face landmarker model cached at `~/.cache/mediapipe/` | ~3 MB download on first use; not persisted across rebuilds (acceptable, unlike 170 MB U2Net) |
| 2026-05-28 | `_face_landmarker` initialised at module level | Landmarker startup is expensive; reuse the same instance across all pipeline calls |
| 2026-05-29 | Op params schema in OPERATIONS list | Single source of truth for slider metadata; app.py renders sliders generically without hardcoding per-op UI logic |
| 2026-05-29 | `FaceNotFoundError` exception instead of silent passthrough | Makes missing detections visible; allows export to skip undetected images cleanly |
| 2026-05-29 | `num_faces=10`, pick largest by bounding box | Handles group photos gracefully without requiring the caller to manage multi-face results |
| 2026-05-29 | Read EXIF bytes from transposed image for export | Original EXIF retains the rotation tag; reading from the transposed copy gets orientation=1, preventing double-rotation in viewers |
| 2026-05-29 | ffmpeg concat demuxer for video creation | More reliable than glob/image2 for non-sequential filenames; sort by mtime preserves capture order regardless of naming convention |
| 2026-05-29 | Semi-transparent strip behind date stamp | H.264 block compression destroys fine text; a dark background region survives encoding and is readable on any background colour |
| 2026-05-29 | Capture `_draw_date` return value at call site | Alpha composite creates a new image object; discarding the return value silently lost all drawing |
| 2026-05-29 | ThreadPoolExecutor for export with `_detect_lock` | rembg/ONNX and Pillow release the GIL so threads run truly in parallel; MediaPipe landmarker is serialised via lock to avoid concurrent calls on a shared instance |
| 2026-05-29 | Export grouped by source folder | Photos from different folders may use different date formats; flat export mixed them unpredictably |
| 2026-05-29 | Per-folder videos merged with ffmpeg `-c copy` | Stream copy avoids re-encoding, preserving quality and making merges fast |
| 2026-05-29 | Frames sorted A→Z by filename for video | More reliable and deterministic than mtime, which can vary across filesystems or after file copies |
| 2026-05-29 | Browse "Select" replaces text area instead of appending | Appending caused silent accumulation of old paths, leading to unintended combined sessions on next Load |
| 2026-05-29 | Staged `_folder_paths_next` key for text area reset | Streamlit forbids modifying a widget-bound key after the widget renders; staging key is consumed before the widget is instantiated on the next rerun |
| 2026-05-29 | `frame_NNNN` naming scoped per folder | Each source folder has an independent sequence; avoids global numbering conflicts when multiple folders are loaded |
| 2026-05-29 | `name` as default `EXPORT_SORT` | Safest fallback when EXIF may be absent or unreliable; A→Z on `frame_NNNN` names always gives correct video order |
| 2026-05-29 | GUI selectbox for sort order seeds from env var | Env var sets the launch default; per-session override available without touching config files |
| 2026-06-05 | Filename date parsing from WP_/WIN_/YYYYMMDD patterns | Many phone cameras embed dates in filenames; parsing them avoids relying on EXIF which can be stripped or wrong |
| 2026-06-05 | Frame size normalisation at read time (before pipeline) | Pipeline ops (align, zoom) must see a consistent canvas; normalising after the pipeline would misalign faces on variably-cropped frames |
| 2026-06-05 | Same `_crop_to_fit` applied in GUI preview | GUI and export must show the same form factor; without this, sliders tuned in preview produce different results in the exported frames |
| 2026-06-05 | Debug export mode as checkbox + env var | Lets users verify which date will stamp each frame before committing to a full export; env var `EXPORT_DEBUG=1` for scripted runs |
| 2026-06-05 | `VIDEO_WIDTH`/`VIDEO_HEIGHT` separate from `EXPORT_WIDTH`/`EXPORT_HEIGHT` | Export frame size and final video resolution are independent concerns; video may need a different resolution target than the per-frame processing canvas |
| 2026-06-05 | ffmpeg stderr truncated to first 2000 + last 500 chars | Full ffmpeg output on failure can exceed 10 000 chars; truncated display keeps the error readable in the Streamlit UI without losing the tail where the actual error usually appears |

---

## External Dependencies & Integrations

- rembg downloads U2Net model from GitHub on first run → requires internet access once.
- MediaPipe face landmarker model (~3 MB) downloaded from Google storage on first use of "Align face" op.

---

## Environment Variables

See `configs/.env.example` for the full list.

| Variable | Purpose |
|----------|---------|
| `DEFAULT_PHOTOS_PATH` | Folder path(s) pre-filled in the GUI on startup |
| `BLUR_RADIUS` | Gaussian blur radius for the background blur op (default: 15) |
| `FACE_ALIGN_X` | Horizontal target position of face centre, 0.0–1.0 (default: 0.5) |
| `FACE_ALIGN_Y` | Vertical target position of face centre, 0.0–1.0 (default: 0.4) |
| `FACE_ZOOM_RATIO` | Target inter-ocular distance as fraction of frame width (default: 0.25) |
| `EXPORT_PATH` | Root export folder; images saved to `EXPORT_PATH/images/<folder>/` (default: `tmp/`) |
| `EXPORT_WORKERS` | Parallel export thread count (default: 4) |
| `EXPORT_SORT` | Frame numbering order: `name` (default) / `date_created` / `date_modified` |
| `EXPORT_WIDTH` | Export frame width in pixels; when both set, images are cover-scaled + center-cropped to this size |
| `EXPORT_HEIGHT` | Export frame height in pixels; same crop applied to GUI preview for consistency |
| `EXPORT_DEBUG` | Set to `1` to replace date stamp with green diagnostic metadata overlay |
| `VIDEO_NAME` | Output video filename without extension (default: `timelapse`) |
| `VIDEO_EXTENSION` | Video container format (default: `mp4`) |
| `VIDEO_FPS` | Frames per second (default: `24`) |
| `VIDEO_CODEC` | ffmpeg video codec (default: `libx264`) |
| `VIDEO_WIDTH` | Video output width in pixels (default: `1920`) |
| `VIDEO_HEIGHT` | Video output height in pixels (default: `1080`) |
| `DATE_FORMAT` | strftime format for the date stamp (default: `%Y-%m-%d`) |
| `DATE_FONT_SIZE` | Font size in px; empty = auto-scale with image height |
| `DATE_TEXT_COLOR` | Date stamp text colour in hex (default: `#FFFFFF`) |
| `DATE_STROKE_COLOR` | Date stamp outline colour in hex (default: `#000000`) |
| `DATE_STROKE_WIDTH` | Date stamp outline thickness in px (default: `2`) |

---

## How to Run

```bash
# Inside the dev container
pip install -r requirements.txt
streamlit run src/app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

## References

- [Original repo: Face-every-day-maker](https://github.com/JohnBetaCode/Face-every-day-maker)
- [Streamlit docs](https://docs.streamlit.io)
- [Pillow EXIF docs](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.getexif)
