from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[1] / "configs" / ".env")

import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps

from pipeline import OPERATIONS, FaceNotFoundError, run_pipeline
from scanner import compute_stats, get_external_devices, scan_folders

st.set_page_config(
    page_title="Face Every Day",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stImage"] img {
    max-height: 78vh !important;
    object-fit: contain;
}
</style>
""", unsafe_allow_html=True)


# ── Folder browser helper ─────────────────────────────────────────────────────

def _render_folder_browser() -> None:
    """
    Two-mode sidebar browser:
      "devices" — lists detected external storage (USB / HDD)
      "browse"  — navigates within the selected device's directory tree
    """
    mode = st.session_state.get("fb_mode", "devices")

    if mode == "devices":
        _render_device_picker()
    else:
        _render_dir_browser()


def _render_device_picker() -> None:
    st.markdown("**External Devices**")
    devices = get_external_devices()

    if not devices:
        st.info("No external devices detected.")
        st.caption("Connect a USB drive or external HDD, then click Browse again.")
    else:
        for dev in devices:
            label = f"💾 {dev['name']}"
            if dev["device"]:
                label += f"  —  `{dev['device']}`"
            if st.button(label, key=f"dev_{dev['mount_point']}", width="stretch"):
                st.session_state.fb_cwd = dev["mount_point"]
                st.session_state.fb_mode = "browse"
                st.rerun()
            st.caption(dev["mount_point"])

    st.divider()
    if st.button("✗ Cancel", width="stretch"):
        st.session_state.fb_open = False
        st.rerun()


def _render_dir_browser() -> None:
    cwd = Path(st.session_state.fb_cwd)

    st.markdown("**Browse folders**")
    st.caption(f"`{cwd}`")

    col_up, col_dev = st.columns(2)
    with col_dev:
        if st.button("⬅ Devices", width="stretch"):
            st.session_state.fb_mode = "devices"
            st.rerun()
    with col_up:
        if cwd.parent != cwd:
            if st.button("⬆ Go up", key="fb_up", width="stretch"):
                st.session_state.fb_cwd = str(cwd.parent)
                st.rerun()

    try:
        subdirs = sorted(
            [d for d in cwd.iterdir() if d.is_dir() and not d.name.startswith(".")],
            key=lambda d: d.name.lower(),
        )
    except PermissionError:
        st.warning("Permission denied.")
        subdirs = []
    except FileNotFoundError:
        st.warning("Directory not found — returning to device list.")
        st.session_state.fb_mode = "devices"
        st.rerun()
        return

    if not subdirs:
        st.info("No subdirectories here.")
    else:
        if len(subdirs) > 30:
            st.caption(f"Showing first 30 of {len(subdirs)} folders.")
        for d in subdirs[:30]:
            if st.button(f"📂 {d.name}", key=f"fb_{d}", width="stretch"):
                st.session_state.fb_cwd = str(d)
                st.rerun()

    st.divider()
    col_sel, col_cancel = st.columns(2)
    with col_sel:
        if st.button("✓ Select", type="primary", width="stretch"):
            st.session_state.folder_paths_text = str(cwd)
            st.session_state.fb_open = False
            st.rerun()
    with col_cancel:
        if st.button("✗ Cancel", width="stretch"):
            st.session_state.fb_open = False
            st.rerun()


# ── Date overlay helper ───────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _draw_date(img: Image.Image, dt) -> Image.Image:
    w, h = img.size
    text = dt.strftime(os.environ.get("DATE_FORMAT", "%Y-%m-%d"))

    env_size = os.environ.get("DATE_FONT_SIZE")
    font_size = int(env_size) if env_size else max(24, h // 20)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    text_color = _hex_to_rgb(os.environ.get("DATE_TEXT_COLOR", "#FFFFFF"))
    stroke_color = _hex_to_rgb(os.environ.get("DATE_STROKE_COLOR", "#000000"))
    stroke_width = int(os.environ.get("DATE_STROKE_WIDTH", "2"))

    # Measure text to position it
    dummy = ImageDraw.Draw(img)
    bbox = dummy.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = max(12, h // 50)
    x = (w - tw) // 2
    y = h - th - pad

    # Semi-transparent dark background strip for readability in video
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([0, y - pad, w, h], fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    ImageDraw.Draw(img).text(
        (x, y), text, font=font, fill=text_color,
        stroke_width=stroke_width, stroke_fill=stroke_color,
    )
    return img


# ── Export helper ────────────────────────────────────────────────────────────

def _sorted_entries(entries: list[dict], sort: str) -> list[dict]:
    if sort == "date_created":
        return sorted(entries, key=lambda e: e["date"])
    if sort == "date_modified":
        return sorted(entries, key=lambda e: Path(e["path"]).stat().st_mtime)
    return sorted(entries, key=lambda e: Path(e["path"]).name)


def _process_one(
    entry: dict, frame_idx: int, pad: int,
    enabled_ops: set[str], op_params: dict, out_dir: Path,
) -> tuple[str, str]:
    src = Path(entry["path"])
    dest_dir = out_dir / src.parent.name
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(src) as orig:
            orig.load()
            frame = ImageOps.exif_transpose(orig).copy()
            exif_bytes = frame.info.get("exif", b"")
        result = run_pipeline(frame, enabled_ops, op_params)
        result = _draw_date(result, entry["date"])
        dest = dest_dir / f"frame_{frame_idx:0{pad}d}{src.suffix.lower()}"
        try:
            result.save(dest, exif=exif_bytes)
        except TypeError:
            result.save(dest)
        os.utime(dest, (entry["date"].timestamp(),) * 2)
        return "exported", ""
    except FaceNotFoundError:
        return "skipped", ""
    except Exception as exc:
        return "error", f"Could not export {src.name}: {exc}"


def _export_all(images: list[dict], enabled_ops: set[str], op_params: dict, out_dir: Path, sort: str = "name") -> None:
    from collections import defaultdict
    out_dir.mkdir(parents=True, exist_ok=True)

    # Group by source folder, sort within each group, assign frame numbers
    by_folder: dict[str, list[dict]] = defaultdict(list)
    for entry in images:
        by_folder[Path(entry["path"]).parent.name].append(entry)

    tasks: list[tuple[dict, int, int]] = []  # (entry, frame_idx, pad)
    for entries in by_folder.values():
        ordered = _sorted_entries(entries, sort)
        pad = max(4, len(str(len(ordered))))
        for idx, entry in enumerate(ordered, 1):
            tasks.append((entry, idx, pad))

    total = len(tasks)
    exported = skipped = errors = 0
    warnings: list[str] = []
    progress = st.progress(0, text="Exporting…")

    workers = min(int(os.environ.get("EXPORT_WORKERS", "4")), total)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_process_one, entry, frame_idx, pad, enabled_ops, op_params, out_dir): entry
            for entry, frame_idx, pad in tasks
        }
        for i, future in enumerate(as_completed(futures)):
            status, msg = future.result()
            if status == "exported":
                exported += 1
            elif status == "skipped":
                skipped += 1
            else:
                errors += 1
                if msg:
                    warnings.append(msg)
            pct = int((i + 1) / total * 100)
            progress.progress((i + 1) / total, text=f"Exporting {i + 1} / {total} ({pct}%)…")

    progress.empty()
    for w in warnings:
        st.warning(w)
    parts = [f"Exported **{exported}** image(s) to `{out_dir}`"]
    if skipped:
        parts.append(f"{skipped} skipped (no face detected)")
    if errors:
        parts.append(f"{errors} error(s)")
    st.success(" · ".join(parts))


# ── Video helper ─────────────────────────────────────────────────────────────

def _ffmpeg(cmd: list[str], spinner_text: str) -> subprocess.CompletedProcess | None:
    """Run an ffmpeg command with a spinner. Returns None if ffmpeg is missing."""
    try:
        with st.spinner(spinner_text):
            return subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        st.error("ffmpeg not found. Install it with `sudo apt-get install ffmpeg` or rebuild the container.")
        return None


def _create_video(images_dir: Path) -> None:
    from scanner import IMAGE_EXTENSIONS

    fps = int(os.environ.get("VIDEO_FPS", "24"))
    name = os.environ.get("VIDEO_NAME", "timelapse")
    ext = os.environ.get("VIDEO_EXTENSION", "mp4").lstrip(".")
    codec = os.environ.get("VIDEO_CODEC", "libx264")

    subfolders = sorted([d for d in images_dir.iterdir() if d.is_dir()]) if images_dir.is_dir() else []
    if not subfolders:
        st.warning(f"No subfolders found in `{images_dir}`. Run **⬇ Export all** first.")
        return

    folder_videos: list[Path] = []

    for folder in subfolders:
        frames = sorted(
            [f for f in folder.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS],
            key=lambda f: f.name,
        )
        if not frames:
            continue

        list_file = images_dir.parent / f"_ffmpeg_{folder.name}.txt"
        list_file.write_text("\n".join(f"file '{f}'" for f in frames))
        folder_video = images_dir.parent / f"{folder.name}.{ext}"

        result = _ffmpeg([
            "ffmpeg", "-y",
            "-r", str(fps), "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c:v", codec, "-pix_fmt", "yuv420p",
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            str(folder_video),
        ], f"Creating `{folder.name}` — {len(frames)} frames…")

        list_file.unlink(missing_ok=True)

        if result is None:
            return
        if result.returncode != 0:
            st.error(f"ffmpeg error (`{folder.name}`):\n```\n{result.stderr[-1000:]}\n```")
            return

        st.info(f"`{folder.name}` — {len(frames)} frames done")
        folder_videos.append(folder_video)

    if not folder_videos:
        st.warning("No images found in any export subfolder.")
        return

    final = images_dir.parent / f"{name}.{ext}"

    if len(folder_videos) == 1:
        folder_videos[0].rename(final)
    else:
        merge_list = images_dir.parent / "_ffmpeg_merge.txt"
        merge_list.write_text("\n".join(f"file '{v}'" for v in folder_videos))

        result = _ffmpeg([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(merge_list),
            "-c", "copy", str(final),
        ], f"Merging {len(folder_videos)} folder videos…")

        merge_list.unlink(missing_ok=True)

        if result is None:
            return
        if result.returncode != 0:
            st.error(f"ffmpeg merge error:\n```\n{result.stderr[-1000:]}\n```")
            return

    st.success(f"Final video saved to `{final}` — {len(folder_videos)} folder(s) merged")


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📸 Face Every Day")
    st.caption("Browse your daily photo archive")
    st.divider()

    # Session state init
    if "folder_paths_text" not in st.session_state:
        st.session_state.folder_paths_text = os.environ.get("DEFAULT_PHOTOS_PATH", "")
    if "fb_open" not in st.session_state:
        st.session_state.fb_open = False
    if "fb_cwd" not in st.session_state:
        st.session_state.fb_cwd = "/"
    if "fb_mode" not in st.session_state:
        st.session_state.fb_mode = "devices"

    if "_load_msg" in st.session_state:
        st.success(st.session_state.pop("_load_msg"))

    # Apply staged path update before the widget is instantiated
    if "_folder_paths_next" in st.session_state:
        st.session_state.folder_paths_text = st.session_state.pop("_folder_paths_next")

    st.text_area(
        "Folder path(s)",
        key="folder_paths_text",
        placeholder="/workspace/photos\n/media/usb-drive",
        help="One path per line. Use Browse to pick folders visually.",
        height=90,
    )

    col_browse, col_load = st.columns([1, 2])
    with col_browse:
        if st.button("Browse…", width="stretch"):
            st.session_state.fb_open = True
            st.session_state.fb_mode = "devices"
            st.rerun()
    with col_load:
        load_clicked = st.button(
            "Load Images", width="stretch", type="primary"
        )

    # Folder browser panel
    if st.session_state.fb_open:
        st.divider()
        _render_folder_browser()

    # Load logic
    if load_clicked:
        paths = list(dict.fromkeys(
            p.strip() for p in st.session_state.folder_paths_text.splitlines() if p.strip()
        ))
        if paths:
            with st.spinner("Scanning folders…"):
                images, corrupted = scan_folders(paths)
            if images:
                prev = len(st.session_state.get("images") or [])
                st.session_state.images = images
                st.session_state.corrupted = corrupted
                st.session_state.stats = compute_stats(images)
                st.session_state.idx = 0
                st.session_state._folder_paths_next = "\n".join(paths)
                msg = f"Loaded {len(images)} image(s)."
                if prev:
                    msg += f" (previous session of {prev} images replaced)"
                st.session_state._load_msg = msg
                st.rerun()
            else:
                st.warning("No readable images found in the given path(s).")
        else:
            st.warning("Enter at least one folder path.")

    # ── Stats panel ───────────────────────────────────────────────────────────
    if st.session_state.get("stats"):
        s = st.session_state.stats
        st.divider()
        st.markdown("#### Summary")
        st.markdown(
            f"<table style='width:100%;font-size:0.82rem;border-collapse:collapse;line-height:1.6'>"
            f"<tr><td style='opacity:.6'>Total</td><td><b>{s['total']}</b> images</td></tr>"
            f"<tr><td style='opacity:.6'>From</td><td><b>{s['min_date']}</b></td></tr>"
            f"<tr><td style='opacity:.6'>To</td><td><b>{s['max_date']}</b></td></tr>"
            f"<tr><td style='opacity:.6'>Days covered</td><td><b>{s['days_with_images']}</b> / {s['total_span_days']}</td></tr>"
            f"<tr><td style='opacity:.6'>Missing</td><td><b>{s['missing_days']}</b> days</td></tr>"
            f"</table>",
            unsafe_allow_html=True,
        )

        if st.session_state.get("corrupted"):
            st.warning(
                f"⚠️ {st.session_state.corrupted} corrupted file(s) skipped"
            )

        st.divider()
        st.markdown("#### By Year")
        for year, ys in s["per_year"].items():
            label = f"{year}  —  {ys['coverage_pct']}% covered"
            with st.expander(label):
                st.progress(ys["coverage_pct"] / 100)
                st.markdown(
                    f"<small style='line-height:1.8'>"
                    f"<b>{ys['images']}</b> images &nbsp;·&nbsp; "
                    f"<b>{ys['days_with_images']}</b> days covered &nbsp;·&nbsp; "
                    f"<b>{ys['missing_days']}</b> / {ys['total_year_days']} missing"
                    f"</small>",
                    unsafe_allow_html=True,
                )

    # ── Pipeline panel ────────────────────────────────────────────────────────
    if st.session_state.get("images"):
        st.divider()
        st.markdown("#### Pipeline")
        enabled_ops: set[str] = set()
        op_params: dict[str, dict] = {}
        for op in OPERATIONS:
            if st.checkbox(op["label"], key=f"op_{op['id']}"):
                enabled_ops.add(op["id"])
                if op.get("params"):
                    op_params[op["id"]] = {}
                    for p in op["params"]:
                        env_str = os.environ.get(p["env"])
                        if env_str is not None:
                            init = int(env_str) if p["type"] == "int" else float(env_str)
                        else:
                            init = p["default"]
                        op_params[op["id"]][p["key"]] = st.slider(
                            p["label"],
                            min_value=p["min"],
                            max_value=p["max"],
                            value=init,
                            step=p["step"],
                            key=f"param_{op['id']}_{p['key']}",
                        )

        st.divider()
        _export_dir = Path(os.environ.get("EXPORT_PATH", str(Path(__file__).parents[1] / "tmp"))) / "images"
        _sort_options = {"Filename (A→Z)": "name", "Date created": "date_created", "Date modified": "date_modified"}
        _sort_default = os.environ.get("EXPORT_SORT", "name")
        _sort_default_label = next((k for k, v in _sort_options.items() if v == _sort_default), "Filename (A→Z)")
        _sort_label = st.selectbox(
            "Frame order",
            options=list(_sort_options.keys()),
            index=list(_sort_options.keys()).index(_sort_default_label),
            key="export_sort",
        )
        _sort = _sort_options[_sort_label]
        if st.button("⬇ Export all", width="stretch", type="primary"):
            _export_all(st.session_state.images, enabled_ops, op_params, _export_dir, _sort)
        if st.button("🎬 Create video", width="stretch"):
            _create_video(_export_dir)
    else:
        enabled_ops = set()
        op_params = {}


# ── Main area ─────────────────────────────────────────────────────────────────

images: list[dict] = st.session_state.get("images", [])

if not images:
    st.markdown("## 👈 Click **Browse…** to pick a folder, then **Load Images**")
    st.stop()

n = len(images)

if "idx" not in st.session_state:
    st.session_state.idx = 0

# ── Navigation ────────────────────────────────────────────────────────────────

col_prev, col_info, col_next = st.columns([1, 10, 1])

with col_prev:
    if st.button("◀", width="stretch", help="Previous image"):
        st.session_state.idx = max(0, st.session_state.idx - 1)

with col_next:
    if st.button("▶", width="stretch", help="Next image"):
        st.session_state.idx = min(n - 1, st.session_state.idx + 1)

with col_info:
    img_info = images[st.session_state.idx]
    st.markdown(
        f"<p style='text-align:center;margin:4px 0;font-size:0.95rem'>"
        f"<b>{img_info['filename']}</b>"
        f" &nbsp;·&nbsp; {img_info['date_str']}"
        f" &nbsp;·&nbsp; {st.session_state.idx + 1} / {n}"
        f"</p>",
        unsafe_allow_html=True,
    )

st.slider("Image position", 0, n - 1, key="idx", label_visibility="collapsed")

# ── Image display ─────────────────────────────────────────────────────────────

try:
    img = ImageOps.exif_transpose(Image.open(img_info["path"]))
except Exception as exc:
    st.error(f"Cannot open image: {exc}")
    st.stop()

col_orig, col_proc = st.columns(2)

with col_orig:
    st.image(img, width="stretch")
    st.caption("Original")

with col_proc:
    try:
        with st.spinner("Running pipeline…"):
            result = run_pipeline(img.copy(), enabled_ops, op_params)
        st.image(result, width="stretch")
    except FaceNotFoundError:
        st.warning("No face detected in this image.")
    except Exception as exc:
        st.error(f"Pipeline error: {exc}")
    st.caption("Processed")
