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
| Container | Docker + VS Code Dev Container | Base image: `python:3.12-slim` |
| Container user | `ada` | Non-root for safer dev |
| Face detection | _TBD_ | dlib or MediaPipe, not started yet |
| Video export | _TBD_ | likely OpenCV or FFmpeg |

---

## Architecture

Single-process Streamlit app. No separate backend — all image scanning and stats run in-process.

```
src/
├── app.py        ← Streamlit entry point  (streamlit run src/app.py)
├── scanner.py    ← Folder scanning, EXIF extraction, stats
└── __init__.py
```

---

## Current Features

- Dev container (Python 3.12, Docker, VS Code)
- Automatic session log via `post-commit` git hook → `docs/session-log.md`
- Web GUI (`src/app.py`) with:
  - Multi-folder path input (one per line, recursive scan)
  - Images sorted newest → oldest by EXIF date (mtime fallback)
  - Prev/Next buttons + full-range slider for navigation
  - Filename, date, and position counter shown per image
  - Sidebar: total images, date range, days covered, missing days
  - Per-year breakdown with coverage % and progress bar
  - Corrupted image detection — skipped with a warning count

---

## In Progress

| Feature | Notes |
|---------|-------|
| Filename date parsing | Third fallback after EXIF and mtime. Format TBD. |

---

## Backlog

- Face detection and alignment before display
- Side-by-side view: raw image left, aligned/processed right
- Timelapse video export (configurable fps, date range, resolution)
- Filter images by year or custom date range in the GUI
- Thumbnail strip / calendar heatmap view
- Filename date parsing (e.g. `2024-03-15_selfie.jpg`, `IMG_20240315.jpg`)

---

## Known Issues / Constraints

- Filename-based date parsing not yet implemented — all date extraction relies on EXIF or file mtime.
- Very large folders may feel slow to scan (no async/caching yet).
- Streamlit's file input doesn't support native OS folder picker; folder path must be typed/pasted.

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

---

## External Dependencies & Integrations

- None yet beyond local filesystem access.

---

## Environment Variables

See `.env.example` for the full list.

| Variable | Purpose |
|----------|---------|
| _none defined yet_ | |

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
