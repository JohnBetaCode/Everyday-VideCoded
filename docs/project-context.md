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
- [ ] Filename-based date parsing as a third fallback
- [ ] Face detection and alignment (dlib or MediaPipe)
- [ ] Side-by-side view: original image + processed result
- [ ] Timelapse video export

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
| Video export | _TBD_ | likely OpenCV or FFmpeg |

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
  - Op 1 · Grayscale
  - Op 2 · Blur background (rembg U2Net segmentation + Gaussian blur, GPU-accelerated; radius via `BLUR_RADIUS` env var)
  - Op 3 · Align face (MediaPipe iris landmarks → rotation + translation; face centred at 50%/40% of frame)
  - Pipeline runs with a spinner in the processed panel while computing

---

## In Progress

| Feature | Notes |
|---------|-------|
| Filename date parsing | Third fallback after EXIF and mtime. Format TBD. |

---

## Backlog

- Timelapse video export (configurable fps, date range, resolution)
- Filter images by year or custom date range in the GUI
- Thumbnail strip / calendar heatmap view
- Filename date parsing (e.g. `2024-03-15_selfie.jpg`, `IMG_20240315.jpg`)

---

## Known Issues / Constraints

- Filename-based date parsing not yet implemented — all date extraction relies on EXIF or file mtime.
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
