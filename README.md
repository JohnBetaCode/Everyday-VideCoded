# everyday2

> A "face every day" maker — browse years of daily self-portraits, align faces automatically, and export a timelapse that shows how you change over time.

Rebuilt from scratch from [Face-every-day-maker](https://github.com/JohnBetaCode/Face-every-day-maker) with a proper web GUI, GPU-accelerated CV pipeline, and a clean dev container.

---

## Table of Contents

- [About](#about)
- [Features](#features)
- [Requirements](#requirements)
- [Setup](#setup)
- [Usage](#usage)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [License](#license)

---

## About

**everyday2** loads one or more folders of daily self-portrait photos, sorts them by date (EXIF → mtime fallback), and lets you browse them with date statistics and a real-time CV pipeline. The pipeline operations — grayscale, background blur, face alignment — stack in order and render side-by-side with the original. The end goal is to produce an aligned timelapse video showing personal change over months and years.

---

## Features

- **Web GUI** — Streamlit app, runs locally, opens in any browser
- **Device picker** — auto-detects USB drives and external HDDs (`/media`, `/run/media`)
- **Multi-folder scan** — one path per line, recursive, deduplicates overlapping paths
- **EXIF-aware sorting** — newest → oldest, with auto-rotation; mtime fallback for photos without metadata
- **Stats dashboard** — total images, date range, days covered, missing days per year with coverage bar
- **Corrupted image handling** — skipped gracefully with a count shown in the sidebar
- **CV pipeline** (side-by-side original vs. processed):
  - **1 · Grayscale** — luminance conversion, RGB output
  - **2 · Blur background** — rembg U2Net segmentation + Gaussian blur (portrait/bokeh effect); GPU-accelerated when an NVIDIA GPU is available
  - **3 · Align face** — MediaPipe Face Mesh iris detection → rotation + translation so the face is centred and eyes are horizontal in every frame
- **GPU support** — NVIDIA GPU passthrough via `nvidia-container-toolkit`; CPU fallback for every op

---

## Requirements

- Docker + VS Code with the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
- _(Optional)_ NVIDIA GPU + [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) for GPU-accelerated background segmentation

No local Python installation needed — everything runs inside the container.

---

## Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd everyday2
```

### 2. Configure your environment

```bash
cp configs/.env.example configs/.env
# Edit configs/.env — set DEFAULT_PHOTOS_PATH to your photo folder
```

### 3. Install git hooks (optional)

```bash
bash scripts/install-hooks.sh
```

After every commit, `docs/session-log.md` is auto-updated using the Claude Code CLI. Requires the [Claude Code CLI](https://claude.ai/code) to be installed and authenticated. The hook skips silently if it isn't.

### 4. Open in dev container

In VS Code: `Ctrl+Shift+P` → **Dev Containers: Reopen in Container**

The first build pulls the CUDA base image and installs all Python dependencies. The U2Net model (~170 MB) is downloaded on first use of "Blur background" and cached in a named Docker volume so it survives rebuilds.

---

## Usage

Once inside the container, start the app:

```bash
streamlit run src/app.py
```

Then open [http://localhost:8501](http://localhost:8501).

1. Type or paste a folder path in the sidebar, or use **Browse…** to pick from connected devices.
2. Click **Load Images**.
3. Use **◀ / ▶** or the slider to navigate.
4. Toggle CV pipeline operations in the sidebar — processed result appears on the right.

---

## Configuration

Copy `configs/.env.example` to `configs/.env` and set values for your local setup.

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_PHOTOS_PATH` | _(empty)_ | Folder path(s) pre-filled in the GUI on startup. Separate multiple paths with `\n`. |
| `BLUR_RADIUS` | `15` | Gaussian blur radius for the background blur op (pixels). Higher = stronger blur. |

---

## Project Structure

```
everyday2/
├── .devcontainer/
│   ├── Dockerfile           # CUDA 12.3 + Python 3.12 + venv
│   ├── docker-compose.yml   # GPU passthrough, media bind mounts, u2net volume
│   └── devcontainer.json    # VS Code dev container config
├── .githooks/
│   └── post-commit          # Auto-updates session log via Claude CLI
├── configs/
│   ├── .env                 # Local overrides (gitignored)
│   └── .env.example         # Committed template
├── docs/
│   ├── project-context.md   # Living project reference
│   ├── session-log.md       # Auto-updated per-session work log
│   └── troubleshooting.md   # Common issues and fixes
├── scripts/
│   └── install-hooks.sh     # Wires up .githooks/
├── src/
│   ├── app.py               # Streamlit entry point
│   ├── pipeline.py          # CV operation registry and cascade runner
│   └── scanner.py           # Folder scan, EXIF extraction, stats
└── requirements.txt
```

---

## License

MIT — see [LICENSE](LICENSE).
