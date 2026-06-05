# Usage Guide

---

## Starting the app

Inside the dev container, run:

```bash
streamlit run src/app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

> **Note:** The first startup takes a few extra seconds — the MediaPipe face landmarker model is initialised at import time. The U2Net background segmentation model (~170 MB) is downloaded on the first use of "Blur background" and cached in a Docker volume for subsequent runs.

---

## Loading images

1. Type or paste one or more folder paths into the **Folder path(s)** text box — one path per line. Subfolders are scanned recursively.
2. Alternatively, click **Browse…** to pick a folder from a connected USB drive or external HDD. The device picker auto-detects volumes mounted under `/media` and `/run/media`.
3. Click **Load Images**. A spinner shows while the folders are being scanned.

Once loaded, the sidebar shows the total image count and any corrupted files that were skipped. If images were already loaded, the previous session is replaced completely and a message confirms this.

> **Note:** Browse **Select** always replaces the text area with the chosen folder — it does not append. Each Load is a clean session.

Supported formats: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.tif`, `.webp`.

---

## Navigating images

Images are sorted **newest → oldest** by EXIF date (falls back to file modification time if no EXIF is present).

- **◀ / ▶ buttons** — step one image at a time.
- **Slider** — jump anywhere in the collection.
- The header bar shows the filename, date, and position counter (`42 / 365`).

---

## Stats panel

Below the load controls the sidebar shows:

- **Total** — number of images loaded.
- **From / To** — date range of the collection.
- **Days covered** — unique calendar days that have at least one photo.
- **Missing** — days in the span with no photo.
- **By Year** — expandable per-year breakdown with image count, days covered, missing days, and a coverage progress bar.

---

## CV pipeline

The pipeline panel appears in the sidebar once images are loaded. Each operation can be toggled independently with a checkbox. Operations are applied in order (1 → 4) and the result is shown side-by-side with the original on the right.

When an operation is enabled, its tunable parameters appear as sliders directly below its checkbox. Slider values are seeded from your `configs/.env` settings and take effect immediately on the current image.

### 1 · Grayscale

Converts the image to luminance and outputs RGB. No parameters.

### 2 · Blur background

Segments the subject using the rembg U2Net model and applies a Gaussian blur to everything outside the mask — a portrait/bokeh effect.

| Slider | Description |
|--------|-------------|
| **Blur radius** | Strength of the background blur in pixels (1–100). Higher values produce a stronger bokeh effect. Env var: `BLUR_RADIUS`. |

> GPU significantly speeds up the U2Net segmentation (~0.3 s vs. ~3 s on CPU).

### 3 · Align face

Detects the face using MediaPipe Face Mesh iris landmarks and applies a rotation + translation so the eyes are horizontal and the face centre lands at the configured position in the frame.

| Slider | Description |
|--------|-------------|
| **Horizontal position** | Target X position of the face centre as a fraction of frame width (0.0–1.0). `0.5` = centred. Env var: `FACE_ALIGN_X`. |
| **Vertical position** | Target Y position of the face centre as a fraction of frame height (0.0–1.0). `0.4` places the eyes slightly above centre; increase to show more forehead. Env var: `FACE_ALIGN_Y`. |

If no face is detected a warning is shown and the processed frame is left empty.

### 4 · Zoom face

Scales the image so the inter-ocular distance (gap between the eyes) occupies a fixed fraction of the frame width, normalising face size across photos taken at different distances.

| Slider | Description |
|--------|-------------|
| **Zoom ratio** | Target inter-ocular distance as a fraction of frame width (0.05–0.50). Lower values zoom out to show more body; higher values zoom in on the face. Env var: `FACE_ZOOM_RATIO`. |

When multiple faces are detected the largest face (by landmark bounding box) is used.

---

## Exporting

Click **⬇ Export all** at the bottom of the pipeline panel to process every loaded image through the current pipeline settings and save the results.

- Output folder: `<EXPORT_PATH>/images/<source_folder>/` — images are grouped by their source folder name, keeping photos from different cameras or naming conventions isolated.
- Frames are renamed `frame_0001.jpg`, `frame_0002.jpg` … (zero-padded, per folder). The sort order that determines the numbering is set via `EXPORT_SORT`:
A **Frame order** selectbox appears in the sidebar above the Export button with three options (default seeded from `EXPORT_SORT` in `configs/.env`):

| Option | `EXPORT_SORT` value | Order |
|--------|---------------------|-------|
| Filename (A→Z) | `name` _(default)_ | Alphabetical by original filename |
| Date created | `date_created` | Chronological by EXIF date (mtime fallback) |
| Date modified | `date_modified` | By file modification time |

- EXIF data and file modification time are carried over from the original photo.
- Each frame is stamped with its capture date (`YYYY-MM-DD`) at the **top centre** using a bold white font on a semi-transparent dark strip. When sort is **Filename (A→Z)** the date is parsed directly from the filename when possible, falling back to EXIF/mtime (see [Filename date parsing](#filename-date-parsing) below).
- Before the pipeline runs, every image is normalised to a consistent canvas: scaled to cover the target size (aspect ratio preserved) and center-cropped. The target size is taken from `EXPORT_WIDTH`/`EXPORT_HEIGHT` if set, otherwise auto-detected from the first image in the batch. This guarantees that face alignment, zoom, and all other ops always operate on a uniform frame size.
- Images where no face is detected are skipped (not exported).
- Existing files are overwritten.

A progress bar shows `N / total (%)` while running. On completion a summary reports how many images were exported, skipped (no face), and any errors.

### Frame size normalisation

Normalisation happens at **read time** — before the pipeline runs — so every op (align, zoom, blur) always sees a consistent canvas. The same crop is applied in the live preview so what you see matches what gets exported.

| Env var | Default | Description |
|---------|---------|-------------|
| `EXPORT_WIDTH` | _(auto)_ | Target frame width in pixels |
| `EXPORT_HEIGHT` | _(auto)_ | Target frame height in pixels |

- **Both set** → every frame is cover-scaled and center-cropped to that exact size.
- **Neither set** (default) → the first image's post-rotation dimensions are used as the reference; all other frames are cropped to match.

Example for a 9:16 portrait format: `EXPORT_WIDTH=1080`, `EXPORT_HEIGHT=1920`.

### Date stamp options

| Env var | Default | Description |
|---------|---------|-------------|
| `DATE_FORMAT` | `%Y-%m-%d` | strftime format string |
| `DATE_FONT_SIZE` | _(auto)_ | Fixed px size; leave empty to scale with image height (`h / 20`) |
| `DATE_TEXT_COLOR` | `#FFFFFF` | Text colour in hex |
| `DATE_STROKE_COLOR` | `#000000` | Outline colour in hex |
| `DATE_STROKE_WIDTH` | `2` | Outline thickness in pixels |

### Filename date parsing

When **Frame order** is set to **Filename (A→Z)**, the app attempts to extract the capture date directly from the filename before falling back to EXIF/mtime. The following patterns are tried in order:

| Pattern | Example | Extracted date |
|---------|---------|----------------|
| `YYYYMMDD_HH_MM_SS` | `WP_20140525_09_31_43_Pro.jpg` | 2014-05-25 09:31:43 |
| `YYYYMMDD_HHMMSS` | `WIN_20140426_123943.JPG` | 2014-04-26 12:39:43 |
| `YYYYMMDD` (isolated 8-digit block) | `20140426_edit.jpg` | 2014-04-26 |

If none of the patterns match (e.g. `IMG_0001.JPG`), the date falls back to EXIF data → file mtime, same as other sort modes.

### Debug export mode

Enable via the **Debug export mode** checkbox in the sidebar (or `EXPORT_DEBUG=1` in `configs/.env`). When active, the normal date stamp is replaced by a green diagnostic overlay in the top-left corner showing:

- **File name** — original filename
- **Filename date** — result of the filename parser (`not parseable` if no pattern matched)
- **EXIF DateTime / DateTimeOriginal / DateTimeDigitized** — all available EXIF date fields
- **File modified / File ctime** — filesystem timestamps
- **Export sort** — the active sort mode

Use this to verify which date will appear on each frame before committing to a full export.

---

## Creating a video

Click **🎬 Create video** to assemble all frames in `<EXPORT_PATH>/images/` into a timelapse video.

- One video is created **per source folder** (e.g. `tmp/2023.mp4`, `tmp/2024.mp4`) and kept alongside the final output — these are not deleted after the merge.
- All folder videos are then **merged into a single final video** (`tmp/timelapse.mp4`).
- Frames within each folder video are ordered alphabetically by frame filename (which reflects the export sort order chosen at export time).
- If the images folder has no subfolders, a warning is shown and nothing happens.
- The final merged video is saved to `<EXPORT_PATH>/<VIDEO_NAME>.<VIDEO_EXTENSION>` (default: `tmp/timelapse.mp4`).

> **Why folder-based?** Photos from different source folders may use different date formats or naming conventions, which can cause ordering issues if mixed into a single flat batch.
- Requires **ffmpeg** to be installed — it is included in the dev container automatically.

| Env var | Default | Description |
|---------|---------|-------------|
| `VIDEO_NAME` | `timelapse` | Output filename without extension |
| `VIDEO_EXTENSION` | `mp4` | Container format |
| `VIDEO_FPS` | `24` | Frames per second |
| `VIDEO_CODEC` | `libx264` | ffmpeg video codec |
| `VIDEO_WIDTH` | `1920` | Output video frame width in pixels |
| `VIDEO_HEIGHT` | `1080` | Output video frame height in pixels |

> **Tip:** Run **⬇ Export all** before **🎬 Create video** to make sure the `images/` folder is up to date with your current pipeline settings.
