from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[1] / "configs" / ".env")

import streamlit as st
from PIL import Image, ImageOps

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
            existing = st.session_state.folder_paths_text.strip()
            st.session_state.folder_paths_text = (
                existing + ("\n" if existing else "") + str(cwd)
            )
            st.session_state.fb_open = False
            st.rerun()
    with col_cancel:
        if st.button("✗ Cancel", width="stretch"):
            st.session_state.fb_open = False
            st.rerun()


# ── Export helper ────────────────────────────────────────────────────────────

def _export_all(images: list[dict], enabled_ops: set[str], op_params: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(images)
    exported = skipped = errors = 0
    progress = st.progress(0, text="Exporting…")

    for i, entry in enumerate(images):
        src = Path(entry["path"])
        try:
            with Image.open(src) as orig:
                orig.load()
                frame = ImageOps.exif_transpose(orig).copy()
                exif_bytes = frame.info.get("exif", b"")
            result = run_pipeline(frame, enabled_ops, op_params)
            dest = out_dir / src.name
            try:
                result.save(dest, exif=exif_bytes)
            except TypeError:
                result.save(dest)
            ts = entry["date"].timestamp()
            os.utime(dest, (ts, ts))
            exported += 1
        except FaceNotFoundError:
            skipped += 1
        except Exception as exc:
            errors += 1
            st.warning(f"Could not export {src.name}: {exc}")
        pct = int((i + 1) / total * 100)
        progress.progress((i + 1) / total, text=f"Exporting {i + 1} / {total} ({pct}%)…")

    progress.empty()
    parts = [f"Exported **{exported}** image(s) to `tmp/`"]
    if skipped:
        parts.append(f"{skipped} skipped (no face detected)")
    if errors:
        parts.append(f"{errors} error(s)")
    st.success(" · ".join(parts))


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
                st.session_state.images = images
                st.session_state.corrupted = corrupted
                st.session_state.stats = compute_stats(images)
                st.session_state.idx = 0
                st.success(f"Loaded {len(images)} image(s).")
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
        if st.button("⬇ Export all", width="stretch", type="primary"):
            _export_all(
                st.session_state.images,
                enabled_ops,
                op_params,
                Path(os.environ.get("EXPORT_PATH", str(Path(__file__).parents[1] / "tmp"))),
            )
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
