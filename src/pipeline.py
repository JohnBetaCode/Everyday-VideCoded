from __future__ import annotations

import math
import os
import urllib.request
from pathlib import Path

import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from PIL import Image, ImageFilter
from rembg import remove

_MODEL_PATH = Path.home() / ".cache" / "mediapipe" / "face_landmarker.task"
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)


class FaceNotFoundError(Exception):
    pass


def _load_face_landmarker() -> mp_vision.FaceLandmarker:
    if not _MODEL_PATH.exists():
        _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
    base_options = mp_python.BaseOptions(model_asset_path=str(_MODEL_PATH))
    options = mp_vision.FaceLandmarkerOptions(base_options=base_options, num_faces=1)
    return mp_vision.FaceLandmarker.create_from_options(options)


# Initialise once at import time — landmarker startup is expensive
_face_landmarker = _load_face_landmarker()


def _grayscale(img: Image.Image) -> Image.Image:
    return img.convert("L").convert("RGB")


def _blur_background(img: Image.Image, params: dict | None = None) -> Image.Image:
    p = params or {}
    radius = int(p.get("blur_radius", os.environ.get("BLUR_RADIUS", 15)))
    mask = remove(img).split()[3]
    blurred = img.filter(ImageFilter.GaussianBlur(radius=radius))
    return Image.composite(img, blurred, mask)


def _detect_iris(img: Image.Image) -> tuple[float, float, float, float] | None:
    """Return (lx, ly, rx, ry) iris pixel coords, or None if no face detected."""
    arr = np.array(img.convert("RGB"))
    h, w = arr.shape[:2]
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
    result = _face_landmarker.detect(mp_image)
    if not result.face_landmarks:
        return None
    lm = result.face_landmarks[0]
    return lm[468].x * w, lm[468].y * h, lm[473].x * w, lm[473].y * h


def _align_face(img: Image.Image, params: dict | None = None) -> Image.Image:
    iris = _detect_iris(img)
    if iris is None:
        raise FaceNotFoundError

    p = params or {}
    lx, ly, rx, ry = iris
    w, h = img.size
    cx, cy = (lx + rx) / 2, (ly + ry) / 2
    angle = math.degrees(math.atan2(ry - ly, rx - lx))
    rotated = img.rotate(angle, center=(cx, cy), resample=Image.Resampling.BICUBIC)

    target_x = w * float(p.get("face_align_x", os.environ.get("FACE_ALIGN_X", 0.5)))
    target_y = h * float(p.get("face_align_y", os.environ.get("FACE_ALIGN_Y", 0.4)))
    dx, dy = target_x - cx, target_y - cy
    return rotated.transform(
        rotated.size,
        Image.AFFINE,
        (1, 0, -dx, 0, 1, -dy),
        resample=Image.Resampling.BICUBIC,
    )


def _zoom_face(img: Image.Image, params: dict | None = None) -> Image.Image:
    """Scale the image so the inter-ocular distance is a fixed fraction of frame width."""
    iris = _detect_iris(img)
    if iris is None:
        raise FaceNotFoundError

    p = params or {}
    lx, ly, rx, ry = iris
    w, h = img.size
    cx, cy = (lx + rx) / 2, (ly + ry) / 2
    ied = math.hypot(rx - lx, ry - ly)

    target_ratio = float(p.get("face_zoom_ratio", os.environ.get("FACE_ZOOM_RATIO", 0.25)))
    scale = (w * target_ratio) / ied

    new_w, new_h = int(w * scale), int(h * scale)
    scaled = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Paste so the face center stays anchored at its original position
    paste_x = int(round(cx - cx * scale))
    paste_y = int(round(cy - cy * scale))
    out = Image.new("RGB", (w, h))
    out.paste(scaled, (paste_x, paste_y))
    return out


OPERATIONS: list[dict] = [
    {
        "id": "grayscale",
        "label": "1 · Grayscale",
        "fn": _grayscale,
    },
    {
        "id": "blur_background",
        "label": "2 · Blur background",
        "fn": _blur_background,
        "params": [
            {"key": "blur_radius", "label": "Blur radius", "type": "int",
             "min": 1, "max": 100, "step": 1, "env": "BLUR_RADIUS", "default": 15},
        ],
    },
    {
        "id": "align_face",
        "label": "3 · Align face",
        "fn": _align_face,
        "params": [
            {"key": "face_align_x", "label": "Horizontal position", "type": "float",
             "min": 0.0, "max": 1.0, "step": 0.05, "env": "FACE_ALIGN_X", "default": 0.5},
            {"key": "face_align_y", "label": "Vertical position", "type": "float",
             "min": 0.0, "max": 1.0, "step": 0.05, "env": "FACE_ALIGN_Y", "default": 0.4},
        ],
    },
    {
        "id": "zoom_face",
        "label": "4 · Zoom face",
        "fn": _zoom_face,
        "params": [
            {"key": "face_zoom_ratio", "label": "Zoom ratio", "type": "float",
             "min": 0.05, "max": 0.50, "step": 0.01, "env": "FACE_ZOOM_RATIO", "default": 0.25},
        ],
    },
]


def run_pipeline(img: Image.Image, enabled: set[str], params: dict | None = None) -> Image.Image:
    params = params or {}
    for op in OPERATIONS:
        if op["id"] in enabled:
            if op.get("params"):
                img = op["fn"](img, params.get(op["id"]))
            else:
                img = op["fn"](img)
    return img
