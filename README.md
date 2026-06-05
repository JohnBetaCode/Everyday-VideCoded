# Everyday Video Maker v2.0 (Claude Vibe Coded)

> A "face every day" maker — browse years of daily self-portraits, align faces automatically, and export a timelapse that shows how you change over time.

Rebuilt from scratch from [Face-every-day-maker](https://github.com/JohnBetaCode/Face-every-day-maker) with a proper web GUI, GPU-accelerated CV pipeline, and a clean dev container.

<p align="center">
  <img src="https://user-images.githubusercontent.com/43115782/121791980-28dca500-cbb5-11eb-99cf-2a2a2a63730f.jpg" width="1200"/>
</p>

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

**everyday2** loads one or more folders of daily self-portrait photos, sorts them by date (EXIF → mtime fallback), and lets you browse them with date statistics and a real-time CV pipeline. The pipeline operations — grayscale, background blur, face alignment, face zoom — stack in order and render side-by-side with the original. Processed images can be batch-exported with original filenames and dates preserved. The end goal is to produce an aligned timelapse video showing personal change over months and years.

<div align="center">

<table width="100%">
  <tr>
    <td align="center" width="33%"><img src="https://user-images.githubusercontent.com/43115782/121792040-f7180e00-cbb5-11eb-9722-5200d20b8169.gif" width="100%"></td>
    <td align="center" width="33%"><img src="https://user-images.githubusercontent.com/43115782/121792067-38a8b900-cbb6-11eb-882e-c2ae489e46af.gif" width="100%"></td>
    <td align="center" width="33%"><img src="https://user-images.githubusercontent.com/43115782/121792038-f4b5b400-cbb5-11eb-8700-3cf72b7d07e5.gif" width="100%"></td>
  </tr>
</table>

</div>


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
  - **3 · Align face** — MediaPipe iris landmarks → rotation + translation so the face is centred and eyes are horizontal in every frame
  - **4 · Zoom face** — scales the image so the inter-ocular distance is a fixed fraction of frame width, normalising face size across photos
  - Each op exposes its parameters as **live sliders** seeded from env vars; changes apply instantly
  - If no face is detected a warning is shown and the processed frame is left empty
  - When multiple faces are present the largest (by landmark bounding box) is used
- **Batch export** — processes all loaded images through the active pipeline, names them `frame_0001.jpg`, `frame_0002.jpg` … per folder (sort order configurable), stamps each frame with its capture date at the top centre; when sort is by filename the date is parsed directly from the filename when possible (supports `WIN_YYYYMMDD_HHMMSS`, `WP_YYYYMMDD_HH_MM_SS_*`, and plain `YYYYMMDD` patterns), falling back to EXIF/mtime
- **Debug export mode** — toggle in the sidebar or via `EXPORT_DEBUG=1`; replaces the normal date stamp with a green diagnostic overlay showing all EXIF date fields, file mtime/ctime, the parsed filename date, and the active sort mode
- **Video creation** — one video per source subfolder (kept alongside the final output), then merged into a single timelapse via ffmpeg; concat files use absolute paths to avoid resolution errors with relative `EXPORT_PATH` values
- **GPU support** — NVIDIA GPU passthrough via `nvidia-container-toolkit`; CPU fallback for every op

---

## Folder organisation advice

> **If photos across time were taken with different cameras, phones, or aspect ratios, keep them in separate subfolders and load each group independently.**
>
> For example, if you switched from iPhone to Android mid-2024, organise your archive as:
> ```
> photos/
> ├── 2024_iphone/    ← Jan – Jun 2024
> ├── 2024_android/   ← Jul – Dec 2024
> └── 2025/
> ```
> Each subfolder is exported and encoded into its own video before being merged into the final timelapse. This prevents resolution mismatches, aspect-ratio jumps, and colour-profile inconsistencies from degrading the merged video.

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

> **Note:** The first load may take a few seconds — the MediaPipe face landmarker model is downloaded and initialized at startup, and the U2Net background segmentation model (~170 MB) is downloaded on the first use of "Blur background".

1. Type or paste a folder path in the sidebar, or use **Browse…** to pick from connected devices.
2. Click **Load Images**.
3. Use **◀ / ▶** or the slider to navigate.
4. Toggle CV pipeline operations in the sidebar — processed result appears on the right. Adjust each op's parameters with the sliders that appear below its checkbox.
5. Click **⬇ Export all** to save all processed images to `EXPORT_PATH/images/`. Each frame gets a date stamp at the top centre. Choose the **Frame order** and optionally enable **Debug export mode** in the sidebar before exporting.
6. Click **🎬 Create video** to assemble the exported frames into a timelapse video.

See [docs/usage.md](docs/usage.md) for a full walkthrough.

---

## Configuration

Copy `configs/.env.example` to `configs/.env` and set values for your local setup.

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_PHOTOS_PATH` | _(empty)_ | Folder path(s) pre-filled in the GUI on startup. Separate multiple paths with `\n`. |
| `BLUR_RADIUS` | `15` | Gaussian blur radius for the background blur op (pixels). |
| `FACE_ALIGN_X` | `0.5` | Horizontal target position of the face centre (0.0–1.0). `0.5` = centred. |
| `FACE_ALIGN_Y` | `0.4` | Vertical target position of the face centre (0.0–1.0). `0.4` = slightly above centre. |
| `FACE_ZOOM_RATIO` | `0.25` | Target inter-ocular distance as a fraction of frame width. Lower = zoom out (more body). |
| `EXPORT_PATH` | `tmp/` | Root export folder; images go to `EXPORT_PATH/images/<folder>/`. |
| `EXPORT_WORKERS` | `4` | Parallel worker threads for export. |
| `EXPORT_SORT` | `name` | Frame ordering within each folder: `name` (A→Z), `date_created` (EXIF), `date_modified` (mtime). |
| `EXPORT_WIDTH` | _(auto)_ | Output frame width in pixels. When both are set, used as the normalisation target; otherwise the first image's dimensions are used automatically. |
| `EXPORT_HEIGHT` | _(auto)_ | Output frame height in pixels. Frames are cover-scaled and center-cropped at read time — before the pipeline runs — so all ops see a consistent canvas. |
| `EXPORT_DEBUG` | _(off)_ | Set to `1` to enable debug overlay (green metadata block instead of date stamp). Also togglable in the sidebar. |
| `VIDEO_NAME` | `timelapse` | Output video filename (without extension). |
| `VIDEO_EXTENSION` | `mp4` | Video container format. |
| `VIDEO_FPS` | `24` | Frames per second. |
| `VIDEO_CODEC` | `libx264` | ffmpeg video codec. |
| `DATE_FORMAT` | `%Y-%m-%d` | strftime format for the date stamp on exported frames. |
| `DATE_FONT_SIZE` | _(auto)_ | Font size in px; leave empty to scale with image height. |
| `DATE_TEXT_COLOR` | `#FFFFFF` | Date stamp text colour (hex). |
| `DATE_STROKE_COLOR` | `#000000` | Date stamp outline colour (hex). |
| `DATE_STROKE_WIDTH` | `2` | Date stamp outline width in pixels. |

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
│   ├── troubleshooting.md   # Common issues and fixes
│   └── usage.md             # Full usage guide
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
