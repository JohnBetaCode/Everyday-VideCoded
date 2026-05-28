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

### 2026-05-28 — Face alignment op, GPU container, config polish

**Goal:** Add a face alignment pipeline operation using MediaPipe FaceLandmarker and harden the GPU container environment for Python 3.12 compatibility.

**Done:**
- Added Op 3 · Align Face: MediaPipe FaceLandmarker (Tasks API) detects iris landmarks 468/473, rotates image to level eyes, translates face centre to 50%/40% of frame
- Added pipeline spinner in processed panel while ops run
- Moved Original/Processed captions below images
- Added `BLUR_RADIUS` env var for configurable background blur strength
- Added MIT LICENSE
- Switched base image to `nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04` to satisfy `onnxruntime-gpu` dependency on `libcublasLt.so.12`
- Added Python venv at `/opt/venv` to avoid `distutils`/pip conflicts
- Added system libs required by MediaPipe: `libgl1`, `libglib2.0-0`, `libgles2`, `libegl1`, `libglx0`
- Fixed `/home/ada/.u2net` root ownership via `mkdir` + `chown` in Dockerfile
- Fixed devcontainer Wayland socket mount error using `containerEnv` override
- Migrated from `mp.solutions` to Tasks API (absent on Python 3.12 / MediaPipe 0.10+)
- Updated README, troubleshooting guide, project-context, and session log

**Decisions:**
- Used MediaPipe Tasks API instead of `mp.solutions` because the latter is unavailable on Python 3.12 with MediaPipe 0.10+
- Chose CUDA 12.3.2 cudnn9 runtime image to provide the exact shared libraries `onnxruntime-gpu` requires without pulling in the full CUDA toolkit

**Next:**
- Add Op 4 or further pipeline stages (e.g. skin tone normalisation, sharpening)
- Validate GPU pipeline end-to-end in the devcontainer with a real NVIDIA device
- Consider caching the MediaPipe model download in the Docker image layer

---
