from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from PIL import Image

from scanner import compute_stats, scan_folders

st.set_page_config(
    page_title="Face Every Day",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Folder browser helper ─────────────────────────────────────────────────────

def _render_folder_browser() -> None:
    """
    Renders an in-sidebar folder browser.
    Navigates the container filesystem and appends the selected path
    to st.session_state.folder_paths_text, then closes itself.
    """
    cwd = Path(st.session_state.fb_cwd)

    st.markdown("**Browse folders**")
    st.caption(f"`{cwd}`")

    # Go up
    if cwd.parent != cwd:
        if st.button("⬆ Go up", key="fb_up", use_container_width=True):
            st.session_state.fb_cwd = str(cwd.parent)
            st.rerun()

    # List subdirectories
    try:
        subdirs = sorted(
            [d for d in cwd.iterdir() if d.is_dir() and not d.name.startswith(".")],
            key=lambda d: d.name.lower(),
        )
    except PermissionError:
        st.warning("Permission denied.")
        subdirs = []
    except FileNotFoundError:
        st.warning("Directory not found — resetting to /.")
        st.session_state.fb_cwd = "/"
        st.rerun()
        return

    if not subdirs:
        st.info("No subdirectories here.")
    else:
        if len(subdirs) > 30:
            st.caption(f"Showing first 30 of {len(subdirs)} folders.")
        for d in subdirs[:30]:
            if st.button(f"📂 {d.name}", key=f"fb_{d}", use_container_width=True):
                st.session_state.fb_cwd = str(d)
                st.rerun()

    st.divider()
    col_sel, col_cancel = st.columns(2)
    with col_sel:
        if st.button("✓ Select", type="primary", use_container_width=True):
            existing = st.session_state.folder_paths_text.strip()
            st.session_state.folder_paths_text = (
                existing + ("\n" if existing else "") + str(cwd)
            )
            st.session_state.fb_open = False
            st.rerun()
    with col_cancel:
        if st.button("✗ Cancel", use_container_width=True):
            st.session_state.fb_open = False
            st.rerun()


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📸 Face Every Day")
    st.caption("Browse your daily photo archive")
    st.divider()

    # Session state init
    if "folder_paths_text" not in st.session_state:
        st.session_state.folder_paths_text = ""
    if "fb_open" not in st.session_state:
        st.session_state.fb_open = False
    if "fb_cwd" not in st.session_state:
        st.session_state.fb_cwd = "/"

    st.text_area(
        "Folder path(s)",
        key="folder_paths_text",
        placeholder="/workspace/photos\n/media/usb-drive",
        help="One path per line. Use Browse to pick folders visually.",
        height=90,
    )

    col_browse, col_load = st.columns([1, 2])
    with col_browse:
        if st.button("Browse…", use_container_width=True):
            st.session_state.fb_open = True
            st.session_state.fb_cwd = "/"
            st.rerun()
    with col_load:
        load_clicked = st.button(
            "Load Images", use_container_width=True, type="primary"
        )

    # Folder browser panel
    if st.session_state.fb_open:
        st.divider()
        _render_folder_browser()

    # Load logic
    if load_clicked:
        paths = [
            p for p in st.session_state.folder_paths_text.splitlines() if p.strip()
        ]
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
        st.metric("Total images", s["total"])
        st.metric("Oldest → Newest", f"{s['min_date']}  →  {s['max_date']}")
        st.metric(
            "Days covered",
            f"{s['days_with_images']} / {s['total_span_days']}",
        )
        st.metric("Missing days (in span)", s["missing_days"])

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
                col_a, col_b = st.columns(2)
                col_a.metric("Images", ys["images"])
                col_b.metric("Days covered", ys["days_with_images"])
                st.metric(
                    "Missing days",
                    f"{ys['missing_days']} / {ys['total_year_days']}",
                )


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
    if st.button("◀", use_container_width=True, help="Previous image"):
        st.session_state.idx = max(0, st.session_state.idx - 1)

with col_next:
    if st.button("▶", use_container_width=True, help="Next image"):
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

st.slider("", 0, n - 1, key="idx", label_visibility="collapsed")

# ── Image display ─────────────────────────────────────────────────────────────

try:
    img = Image.open(img_info["path"])
    st.image(img, use_container_width=True)
except Exception as exc:
    st.error(f"Cannot display image: {exc}")
