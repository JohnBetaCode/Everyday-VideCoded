# Session Log

A running log of each working session — what was built, why, and any decisions worth remembering.

---

## Template

```
### YYYY-MM-DD — <short title>

**Goal:** What we set out to do.

**Done:**
- ...

**Decisions:**
- ...

**Next:**
- ...
```

---

## Sessions

### 2026-05-25 — Initial repo setup

**Goal:** Bootstrap the project structure and development environment.

**Done:**
- Created Python 3.12 dev container with `Dockerfile` and `docker-compose.yml`
- Added `devcontainer.json` so VS Code can open the repo in-container
- Created `README.md` and `docs/session-log.md`

**Decisions:**
- Used `python:3.12-slim` as the base image to keep the image light
- Created a non-root user `ada` inside the container for safer development

**Next:**
- Fill in `README.md` with project description and setup instructions

### 2026-05-25 — Streamlit GUI, image scanner, and devcontainer setup

**Goal:** Build a Streamlit web app for browsing and auditing a photo library, with EXIF-based image scanning and a containerized development environment.

**Done:**
- Added `src/app.py`: Streamlit app with sidebar folder browser, image navigation, and per-year missing-days statistics
- Added `src/scanner.py`: scans folders for images using EXIF date extraction, mtime fallback, and corrupted image detection
- Added `.devcontainer/devcontainer.json` and updated `docker-compose.yml` to mount `/media`, `/mnt`, `/run/media` read-only for USB/HDD access
- Added `.githooks/post-commit` hook that auto-updates `docs/session-log.md` via Claude CLI after each commit
- Added `scripts/install-hooks.sh` to wire up the git hook
- Added `README.md` with setup instructions and project structure overview
- Added `docs/project-context.md` as a living project reference
- Added `docs/session-log.md` as the per-session work log (this file)

**Decisions:**
- External media mounts are read-only in the devcontainer to prevent accidental writes to photo drives
- EXIF extraction falls back to mtime so images without metadata are still dated
- Session log is auto-updated by a post-commit hook rather than manually maintained

**Next:**
- Add duplicate detection across scanned folders
- Support filtering/search within the Streamlit app (by date range, folder, or missing-day gaps)
- Consider caching scanner results to avoid rescanning large libraries on every run

---

### 2026-05-27 — External device browser, image fixes, dev env config

**Goal:** Replace the root-based folder browser with a device picker and fix image rendering issues while cleaning up the dev environment setup.

**Done:**
- Folder browser now starts with a USB/HDD device picker (via `/media`, `/run/media`, `/proc/mounts`) instead of browsing from `/`
- EXIF auto-rotation applied via `ImageOps.exif_transpose` to fix inverted images
- CSS `max-height: 78vh` added to keep images in viewport regardless of window size
- Sidebar stats replaced with compact HTML table (removed bulky `st.metric`)
- Duplicate folder paths deduplicated before scanning
- `configs/.env` with `DEFAULT_PHOTOS_PATH` loaded at startup via `python-dotenv`; `configs/.env.example` committed as template
- Fixed Streamlit deprecations: `use_container_width` → `width=`, empty slider label
- Added `.gitignore` and `docs/troubleshooting.md`

**Decisions:**
- Device picker scoped to `/media`, `/run/media`, and `/proc/mounts` rather than a full filesystem walk — keeps the UI focused on external/removable media
- `.env` kept out of version control; `.env.example` committed as the canonical reference

**Next:**
- Add filtering/sorting options to the image browser
- Consider caching scan results to speed up large folders

---

### 2026-05-28 — Face alignment, GPU container, config improvements

**Goal:** Add face alignment to the CV pipeline, fix GPU support in the dev container, and polish the app config and docs.

**Done:**
- Added **Op 3 · Align face** to `src/pipeline.py`: MediaPipe Tasks API (`FaceLandmarker`) detects iris landmarks (indices 468/473) → compute rotation angle from eye vector → rotate image → translate eye midpoint to 50%/40% of frame
- Added pipeline **loading spinner** in the processed panel while ops run
- Moved "Original" / "Processed" captions **below** the images
- Added `BLUR_RADIUS` env var to control background blur strength; added to `configs/.env.example`
- Added **MIT LICENSE** file
- Switched dev container base image from `python:3.12-slim` to `nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04` so `onnxruntime-gpu` can find CUDA libs
- Added Python **venv at `/opt/venv`** to avoid pip conflicts with apt-managed distutils packages in the CUDA image
- Fixed **`/home/ada/.u2net` permission denied**: pre-create directory with `ada` ownership in Dockerfile; delete old volume with `docker volume rm devcontainer_u2net-cache` to reinitialise
- Fixed **devcontainer Wayland socket error**: added `containerEnv: {WAYLAND_DISPLAY: ""}` to `devcontainer.json`; root cause was `/run/user/1000/wayland-0` becoming a directory instead of a socket after a failed mount
- Fixed **missing OpenGL/EGL libs** for mediapipe: added `libgl1 libglib2.0-0 libgles2 libegl1 libglx0` to apt installs
- Switched mediapipe from `mp.solutions.face_mesh` (not available on Python 3.12 / mediapipe 0.10+) to **Tasks API** (`FaceLandmarker.create_from_options`)
- Updated README.md, troubleshooting.md, project-context.md

**Decisions:**
- MediaPipe Tasks API over dlib: `mp.solutions` is absent in mediapipe 0.10+ on Python 3.12; Tasks API works and exposes the same 478-landmark model with iris centers
- Face landmarker model (~3 MB) cached at `~/.cache/mediapipe/` — small enough to re-download on rebuild, no new Docker volume needed
- `_face_landmarker` and related objects initialised at module import time to avoid per-call startup cost

**Next:**
- Verify GPU is active for rembg once CUDA container is stable
- Consider persisting the MediaPipe model in a Docker volume if cold-start download becomes annoying
- Filename date parsing (third fallback after EXIF and mtime)

---

### 2026-05-29 — Pipeline sliders, export, video creation, and date stamp

**Goal:** Complete the core export and video pipeline: zoom face op, interactive param sliders, batch export, video creation with ffmpeg, and a date stamp on every exported frame.

**Done:**
- **Op 4 · Zoom face** (`src/pipeline.py`): scales image so inter-ocular distance matches `FACE_ZOOM_RATIO` fraction of frame width; extracted shared `_detect_iris()` helper reused by align and zoom ops
- **Pipeline param sliders**: each op now exposes tunable params as sidebar sliders seeded from env vars (`BLUR_RADIUS`, `FACE_ALIGN_X/Y`, `FACE_ZOOM_RATIO`); changes apply immediately on the current image
- **`FaceNotFoundError`**: align and zoom ops raise this instead of silently returning the original; app shows a warning and leaves the processed frame empty
- **Multi-face handling**: `num_faces` raised to 10; largest face by landmark bounding box is selected
- **⬇ Export all** button: processes all loaded images through the current pipeline + sliders, saves to `EXPORT_PATH/images/` preserving original filenames, EXIF bytes, and file mtime; face-not-found images are skipped; progress bar shows `N / total (%)`
- **Fixed double-rotation on export**: `exif_bytes` now read from the transposed image (orientation tag = 1) rather than the original (which still carried the rotation tag)
- **🎬 Create video** button: reads all frames from `EXPORT_PATH/images/` sorted by mtime, writes an ffmpeg concat list, invokes `ffmpeg`; configurable via `VIDEO_NAME`, `VIDEO_EXTENSION`, `VIDEO_FPS`, `VIDEO_CODEC`; gracefully handles missing ffmpeg
- **ffmpeg** added to `apt-get install` in `.devcontainer/Dockerfile`
- **Date stamp on exported frames**: `_draw_date()` overlays `YYYY-MM-DD` at bottom centre using DejaVu Sans Bold with a semi-transparent dark background strip for H.264 resilience; configurable via `DATE_FORMAT`, `DATE_FONT_SIZE`, `DATE_TEXT_COLOR`, `DATE_STROKE_COLOR`, `DATE_STROKE_WIDTH`
- Fixed stale image reference in `_draw_date`: alpha composite creates a new object, so the call site now captures the return value
- Created `docs/usage.md` with a full feature walkthrough
- Synced README, `docs/project-context.md`, and `docs/usage.md` with all new features

**Decisions:**
- Inter-ocular distance as a fraction of frame width (not pixels) keeps zoom resolution-independent
- `FaceNotFoundError` as an explicit exception (vs. returning `None`) makes failures visible and prevents silent data corruption in exports
- Largest bounding-box face chosen as the prominence heuristic for multi-face frames
- mtime sort for video frame order reflects original capture date regardless of filename convention
- Semi-transparent background strip behind date text survives H.264 block-based compression better than text stroke alone
- ffmpeg concat demuxer used over glob/image2 for reliable ordering with non-sequential filenames

**Next:**
- Filename-based date parsing (third fallback after EXIF and mtime)
- Async/cached folder scanning for large collections
- Filter images by year or date range in the GUI

---

### 2026-05-29 — Consolidate session log and sync all docs

**Goal:** Replace 13 fragmented auto-hook session entries with one comprehensive entry and sync README, project-context, and usage docs to reflect completed work.

**Done:**
- Consolidated 13 small auto-hook session log entries into a single comprehensive session entry in `docs/session-log.md`
- Updated `README.md` with video creation workflow, date stamp feature, and new env vars
- Updated `docs/project-context.md` with current project state and completed goals
- Updated `docs/usage.md` with date stamp configuration and new env var documentation

**Decisions:**
- Chose to consolidate fragmented auto-hook entries into a single session log entry for readability rather than keeping the granular auto-generated history

**Next:**
- Continue building on the video creation and date stamp features now that docs are current

---

### 2026-05-29 — Parallel export, folder-based output, per-folder video, and session reset

**Goal:** Speed up export with threads, organise output by source folder, generate per-folder videos that merge into a final timelapse, and fix session contamination when switching folders.

**Done:**
- **Parallel export**: `ThreadPoolExecutor` dispatches per-image work concurrently; `EXPORT_WORKERS` env var (default 10) controls pool size; `_detect_lock` in `pipeline.py` serialises the shared MediaPipe landmarker instance; progress updates via `as_completed()` on the main thread
- **Folder-based export**: images saved to `EXPORT_PATH/images/<source_folder>/` — photos from different folders stay isolated, avoiding date-format mixing
- **Per-folder video + merge**: `🎬 Create video` builds one video per subfolder (frames sorted A→Z by filename), then merges all into `EXPORT_PATH/VIDEO_NAME.EXT` using ffmpeg concat with stream copy (no re-encode)
- **Fresh session on load**: Browse "Select" now replaces the text area instead of appending; after a successful load the text area resets to exactly the scanned paths and the page reruns; a message is shown when a previous session is replaced
- **Streamlit staging fix**: `folder_paths_text` (widget-bound key) cannot be set after the widget renders — introduced `_folder_paths_next` staging key consumed before the widget is instantiated on the next rerun

**Decisions:**
- Threads over processes: rembg/ONNX and Pillow release the GIL, giving real parallelism without multiprocessing overhead
- Source-folder grouping: avoids filename/date-format collisions between folders
- ffmpeg `-c copy` for merge: stream copy preserves quality and is fast since all source videos share the same codec/settings
- A→Z filename sort for video: more deterministic than mtime across filesystems and after file copies
- Replace-over-append for Browse Select: appending was the root cause of unintentional combined sessions

**Next:**
- Filename-based date parsing (third fallback after EXIF and mtime)
- Option to clean up intermediate per-folder video artifacts after merge

**Next:**
- Monitor for similar widget-bound state mutation patterns elsewhere in the app

---

### 2026-05-29 — Frame naming, sort order UI, and video polish

**Goal:** Give exported frames consistent sequential names, expose sort order as a GUI control, and confirm video creation uses the correct frame order and overwrites existing files.

**Done:**
- Exported frames renamed to `frame_0001.ext`, `frame_0002.ext` … (zero-padded, per source folder)
- Added **Frame order** selectbox in the sidebar above Export all: `Filename (A→Z)` / `Date created` / `Date modified`; default seeded from `EXPORT_SORT` env var
- `EXPORT_SORT` added to `configs/.env.example`
- Video creation already sorts frames A→Z by filename — `frame_0001`, `frame_0002` … are naturally ordered correctly
- Both per-folder and merge ffmpeg calls already carry `-y` — existing videos are overwritten silently
- Added folder organisation section to README advising users to keep mixed-camera or mixed-phone batches in separate subfolders to avoid resolution/aspect-ratio mismatches in the merged video
- Synced all docs with the day's work

**Decisions:**
- Zero-padding scoped per folder (not global) so each input directory has its own independent `frame_0001`
- `name` (A→Z) as default sort order — safest fallback when EXIF may be absent or unreliable
- GUI selectbox takes precedence over env var each session; env var sets the launch default

**Next:**
- Filename-based date parsing (third fallback after EXIF and mtime)
- Option to clean up intermediate per-folder video artifacts after merge

---

### 2026-05-29 — End-of-day sync: frame naming, sort UI, video polish

**Goal:** Consolidate small session entries and update documentation to reflect frame_NNNN naming, EXPORT_SORT, video overwrite behaviour, and key decisions.

**Done:**
- Updated `docs/project-context.md` with frame_NNNN naming convention, EXPORT_SORT option, video overwrite behaviour, and new key decisions
- Condensed `docs/session-log.md` by merging remaining small session entries
- Updated `docs/usage.md` with Frame order selectbox details

**Decisions:**
- frame_NNNN naming adopted as the standard export frame format
- EXPORT_SORT option added to control frame ordering in exports
- Video overwrite behaviour documented as an explicit decision

**Next:**
- Continue implementing features informed by the updated project context

---

### 2026-06-05 — Filename date parsing, frame size normalisation, debug mode, and video resolution

**Goal:** Add the remaining core features: parse dates from filenames, normalise all frames to a consistent canvas before the pipeline runs, add a debug overlay for verifying date metadata, and expose video output resolution as env vars.

**Done:**
- **Filename date parsing** (`_FILENAME_DATE_PATTERNS` in `app.py`): when sort=name, three patterns tried in order — `WP_YYYYMMDD_HH_MM_SS_*`, `WIN_YYYYMMDD_HHMMSS`, isolated `YYYYMMDD` block; falls back to EXIF → mtime if none match; parsed date used for the frame's date stamp
- **Debug export mode** (`_draw_debug_dates` in `app.py`): toggled via `EXPORT_DEBUG=1` env var or the sidebar checkbox; replaces the normal date stamp with a green diagnostic block showing filename, filename-parsed date, all EXIF DateTime fields, file mtime/ctime, and active sort mode; useful for verifying date metadata before a full export run
- **Export frame size normalisation** (`_crop_to_fit` in `app.py`, `_export_all`): every exported frame is cover-scaled and center-cropped to `EXPORT_WIDTH×EXPORT_HEIGHT`; if env vars are not set, the first image's post-rotation dimensions are used as the reference canvas so all frames in a batch are the same size
- **Normalisation moved to read time** (before the pipeline): pipeline ops (align, zoom, blur) now always see a consistent canvas; previously normalisation happened after the pipeline, which caused misaligned faces on frames that differed in aspect ratio
- **Same crop in GUI preview** (`app.py` lines 704–707): `_crop_to_fit` is applied when rendering the preview image, so the form factor displayed in the browser matches what will be exported; slider tuning in the preview now accurately reflects export output
- **Configurable video resolution** (`VIDEO_WIDTH`/`VIDEO_HEIGHT` in `_create_video`): ffmpeg `scale+pad` filter applied to final video; defaults to 1920×1080; even dimensions enforced for h264 compatibility
- **Better ffmpeg error display**: stderr output truncated to first 2000 + last 500 chars to keep the Streamlit error panel readable on failure
- Added `EXPORT_WIDTH`, `EXPORT_HEIGHT`, `EXPORT_DEBUG`, `VIDEO_WIDTH`, `VIDEO_HEIGHT` to `configs/.env.example`
- Synced all docs with the session's work

**Decisions:**
- Normalisation at read time, not after pipeline — pipeline ops must see a consistent canvas or face alignment and zoom produce wrong results on mixed-aspect-ratio batches
- GUI preview applies the same crop as export — so what you tune on screen is what you get in the output file
- `VIDEO_WIDTH`/`VIDEO_HEIGHT` kept separate from `EXPORT_WIDTH`/`EXPORT_HEIGHT` — final video resolution and per-frame processing canvas are independent concerns
- ffmpeg stderr truncation: first 2000 chars catches the preamble and codec info; last 500 chars captures the actual error that stops encoding

**Next:**
- Filter images by year or date range in the GUI
- Async/cached scanning for large collections

---
