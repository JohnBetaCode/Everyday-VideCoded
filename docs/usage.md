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

Once loaded, the sidebar shows the total image count and any corrupted files that were skipped.

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

- Output folder: `<EXPORT_PATH>/images/` — configured via `EXPORT_PATH` in `configs/.env`, defaults to `tmp/` in the project root.
- Filenames are preserved from the source.
- EXIF data and file modification time are carried over from the original photo.
- Each frame is stamped with its capture date (`YYYY-MM-DD`) at the bottom centre using a bold white font on a semi-transparent dark strip.
- Images where no face is detected are skipped (not exported).
- Existing files are overwritten.

A progress bar shows `N / total (%)` while running. On completion a summary reports how many images were exported, skipped (no face), and any errors.

### Date stamp options

| Env var | Default | Description |
|---------|---------|-------------|
| `DATE_FORMAT` | `%Y-%m-%d` | strftime format string |
| `DATE_FONT_SIZE` | _(auto)_ | Fixed px size; leave empty to scale with image height (`h / 20`) |
| `DATE_TEXT_COLOR` | `#FFFFFF` | Text colour in hex |
| `DATE_STROKE_COLOR` | `#000000` | Outline colour in hex |
| `DATE_STROKE_WIDTH` | `2` | Outline thickness in pixels |

---

## Creating a video

Click **🎬 Create video** to assemble all frames in `<EXPORT_PATH>/images/` into a timelapse video.

- Frames are ordered by file modification time, which matches the original photo date set during export.
- If the images folder is empty or missing, a warning is shown and nothing happens.
- The output video is saved to `<EXPORT_PATH>/<VIDEO_NAME>.<VIDEO_EXTENSION>` (default: `tmp/timelapse.mp4`).
- Requires **ffmpeg** to be installed — it is included in the dev container automatically.

| Env var | Default | Description |
|---------|---------|-------------|
| `VIDEO_NAME` | `timelapse` | Output filename without extension |
| `VIDEO_EXTENSION` | `mp4` | Container format |
| `VIDEO_FPS` | `24` | Frames per second |
| `VIDEO_CODEC` | `libx264` | ffmpeg video codec |

> **Tip:** Run **⬇ Export all** before **🎬 Create video** to make sure the `images/` folder is up to date with your current pipeline settings.
