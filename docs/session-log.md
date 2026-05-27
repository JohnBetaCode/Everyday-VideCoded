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
