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

### 2026-05-29 — Zoom face pipeline op and configurable face position env vars

**Goal:** Add a zoom-face pipeline operation that scales the image to a target inter-ocular distance ratio, and expose env vars for controlling face placement.

**Done:**
- Added op 4 · Zoom face to `src/pipeline.py`, scaling images so inter-ocular distance matches `FACE_ZOOM_RATIO` (default 0.10) fraction of frame width
- Extracted shared `_detect_iris()` helper reused by both align and zoom ops
- Added `FACE_ALIGN_X` and `FACE_ALIGN_Y` env vars to control face position in the frame
- Updated `configs/.env.example` with new env var documentation

**Decisions:**
- Inter-ocular distance expressed as a fraction of frame width (not pixels) to stay resolution-independent
- Shared iris detection logic extracted into a helper rather than duplicated across ops

**Next:**
- Consider op 5 for additional face normalization steps (expression, lighting)
- Evaluate whether zoom and align ops should be composable in a single pass

---

### 2026-05-29 — Pipeline param sliders and face-not-found warning

**Goal:** Expose tunable pipeline parameters as interactive sidebar sliders and surface missing face detections as an explicit error instead of silent fallback.

**Done:**
- Added sidebar sliders for each pipeline op's tunable params (`BLUR_RADIUS`, `FACE_ALIGN_X/Y`, `FACE_ZOOM_RATIO`), seeded from env vars
- Slider changes immediately rerun the pipeline on the current image
- Introduced `FaceNotFoundError` so align/zoom ops signal missing detections cleanly
- App shows a warning and leaves the processed frame empty on `FaceNotFoundError` instead of silently returning the original image
- Updated `.env.example` to reflect new/changed env var names

**Decisions:**
- Env vars serve as defaults for sliders rather than hard-coded values, keeping configuration externally overridable
- `FaceNotFoundError` as a distinct exception type (vs. returning `None` or a sentinel) makes failure explicit and avoids silent data corruption downstream

**Next:**
- Add sliders or controls for any remaining pipeline ops not yet parameterized
- Consider persisting slider state across sessions

---

### 2026-05-29 — Export all images with pipeline applied

**Goal:** Add a bulk export feature that processes all loaded images through the current pipeline and saves them to `tmp/` with metadata preserved.

**Done:**
- Added "Export all" button to the pipeline sidebar panel (`src/app.py`)
- Processes every loaded image through the current pipeline and params
- Saves output to `tmp/` using original filenames
- Copies EXIF bytes and sets file mtime to the original photo date
- Skips images where no face is detected (counted separately, not as errors)
- Progress bar tracks export progress; summary shown on completion

**Decisions:**
- Face-not-found treated as a skip rather than an error, keeping export results clean
- Output directory fixed to `tmp/` for consistency with prior export conventions

**Next:**
- Allow user to configure output directory
- Option to open `tmp/` in file manager after export

---

### 2026-05-29 — Configurable export folder via env var

**Goal:** Allow the export output directory to be configured through an `EXPORT_PATH` environment variable instead of being hardcoded.

**Done:**
- Added `EXPORT_PATH` entry to `configs/.env.example` with documentation
- Updated `src/app.py` to read export path from `EXPORT_PATH` env var

**Decisions:**
- Used an environment variable for configuration to keep deployment-specific paths out of source code

**Next:**
- Document the new env var in the project README or setup guide

---

### 2026-05-29 — Show percentage in export progress bar

**Goal:** Display a percentage indicator in the export progress bar to give users clearer feedback during export.

**Done:**
- Updated `src/app.py` to show percentage alongside the progress bar during export

**Decisions:**
- N/A

**Next:**
- Consider adding estimated time remaining to the progress display

---

### 2026-05-29 — Fix double-rotation on image export

**Goal:** Prevent exported images from being rotated twice by reading EXIF bytes from the already-transposed image rather than the original.

**Done:**
- Fixed `src/app.py` to extract `exif_bytes` after transposing the image, so the rotation tag no longer reflects a correction that has already been applied to the pixels.

**Decisions:**
- Read EXIF data post-transpose so the embedded orientation tag matches the actual pixel orientation, avoiding double-rotation in viewers that honor EXIF.

**Next:**
- Verify exported images render correctly in EXIF-aware viewers (e.g. macOS Preview, web browsers).

---

### 2026-05-29 — Pick largest face in multi-face frames

**Goal:** Ensure the most prominent subject is always selected when multiple faces appear in a photo.

**Done:**
- Raised `num_faces` from its previous limit to 10 to detect all candidates in a frame
- Added logic in `src/pipeline.py` to select the face with the largest landmark bounding box

**Decisions:**
- Largest bounding box used as the prominence heuristic — closest/most prominent subject in group photos or accidental multi-face captures

**Next:**
- Consider fallback behavior when no faces are detected after raising the limit

---

### 2026-05-29 — Add startup time warning to README

**Goal:** Warn users in the README about the slow first-run startup caused by model loading.

**Done:**
- Added a startup time warning note to `README.md` advising users to expect a delay on first launch

**Decisions:**
- N/A

**Next:**
- Consider lazy-loading models or showing an in-app spinner to reduce perceived startup time

---

### 2026-05-29 — Add usage guide covering all app features

**Goal:** Document all application features in a comprehensive usage guide for developers and users.

**Done:**
- Created `docs/usage.md` with 106 lines covering all app features

**Decisions:**
- N/A

**Next:**
- Keep usage guide updated as new features are added

---

### 2026-05-29 — Sync README and project-context with current feature set

**Goal:** Bring documentation up to date with the current state of the project by updating both the README and project-context reference file.

**Done:**
- Updated README features list, configuration table, usage steps, and project structure
- Updated `docs/project-context.md` with current goals, features, env vars, key decisions, and backlog

**Decisions:**
- N/A

**Next:**
- Continue backlog items tracked in `docs/project-context.md`

---

### 2026-05-29 — Save exported images to images/ subfolder within export path

**Goal:** Organise exported images into a dedicated `images/` subfolder inside the configured export directory.

**Done:**
- Updated `src/app.py` to write exported images to `<EXPORT_PATH>/images/` instead of directly into `<EXPORT_PATH>`

**Decisions:**
- N/A

**Next:**
- Consider creating additional subfolders (e.g. by date or batch) for larger exports

---

### 2026-05-29 — Create video button using ffmpeg from exported images

**Goal:** Add a "Create video" button to the pipeline panel that assembles exported images into a video using ffmpeg.

**Done:**
- Added "Create video" button below "Export all" in the pipeline panel (`src/app.py`)
- Images in `EXPORT_PATH/images/` are sorted by mtime to preserve original photo date order
- ffmpeg is invoked with a concat list; output is configurable via `VIDEO_NAME`, `VIDEO_EXTENSION`, `VIDEO_FPS`, and `VIDEO_CODEC` env vars
- Added warning dialog when no images exist in the export folder
- Surfaces ffmpeg stderr output if the command fails
- Documented new env vars in `configs/.env.example`

**Decisions:**
- Sort by mtime rather than filename to reflect original capture order regardless of naming convention
- Expose codec and FPS as env vars to avoid hardcoding format assumptions

**Next:**
- Consider a progress indicator for long ffmpeg runs
- Add option to open the output video file after creation

---

### 2026-05-29 — Install ffmpeg in container and handle missing ffmpeg gracefully

**Goal:** Ensure ffmpeg is available in the dev container and that the app degrades gracefully when it is absent.

**Done:**
- Added ffmpeg installation to `.devcontainer/Dockerfile`
- Updated `src/app.py` to detect missing ffmpeg and handle the error gracefully

**Decisions:**
- Handled missing ffmpeg at runtime rather than hard-failing, allowing the app to remain usable without video export capability

**Next:**
- Test video export end-to-end in the container environment

---

### 2026-05-29 — README polish and image gitignore

**Goal:** Update the README with a cleaner title and preview images while excluding image files from version control.

**Done:**
- Updated README title and added preview image references
- Added image file patterns to `.gitignore` to keep binary assets out of the repo

**Decisions:**
- Preview images are referenced in the README but not tracked in git, keeping the repo lightweight

**Next:**
- Host or link preview images externally if needed for public visibility

---

### 2026-05-29 — Date stamp on exported frames

**Goal:** Overlay the capture date on each exported frame as a readable watermark.

**Done:**
- Added date stamping to exported frames in `src/app.py` with white text and black stroke
- Set font size proportional to image height for consistent appearance across resolutions
- Added fallback to Pillow's built-in font when DejaVu is unavailable

**Decisions:**
- Bottom-center placement for the date stamp
- Proportional font sizing rather than a fixed pixel size to handle varying image dimensions
- Graceful degradation to built-in font keeps the feature working without system font dependencies

**Next:**
- Consider making stamp position or size configurable via UI or settings

---

### 2026-05-29 — Make date stamp configurable via env vars

**Goal:** Expose date stamp rendering options as environment variables so users can customize the overlay without touching source code.

**Done:**
- Added `DATE_FORMAT`, `DATE_FONT_SIZE`, `DATE_TEXT_COLOR`, `DATE_STROKE_COLOR`, and `DATE_STROKE_WIDTH` env vars
- Documented all new variables in `configs/.env.example`
- Updated `src/app.py` to read and apply these settings at runtime

**Decisions:**
- Used environment variables (rather than a config file or CLI flags) to keep customization lightweight and container-friendly

**Next:**
- Consider adding validation or fallback defaults for malformed env var values

---

### 2026-05-29 — Fix date stamp visibility in video frames

**Goal:** Make the date stamp survive H.264 compression and remain readable on any background.

**Done:**
- Added semi-transparent dark background strip behind date stamp text in `src/app.py`
- Switched font to DejaVu Sans Bold for better legibility at small sizes
- Fixed stale image reference by capturing return value from `_draw_date` (alpha composite returns a new object)

**Decisions:**
- Dark background strip chosen over font outline/shadow as a more compression-resilient approach

**Next:**
- Re-export existing images to pick up the visibility fix

---
