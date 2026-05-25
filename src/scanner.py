from __future__ import annotations

from calendar import isleap
from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image

IMAGE_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp",
})

# Map tag name → numeric EXIF tag ID for the three date fields we care about
_DATE_TAG_IDS: dict[str, int] = {
    name: tag_id
    for tag_id, name in ExifTags.TAGS.items()
    if name in ("DateTimeOriginal", "DateTimeDigitized", "DateTime")
}


def _exif_date(img: Image.Image) -> datetime | None:
    try:
        exif = img.getexif()
        for tag_name in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
            tag_id = _DATE_TAG_IDS.get(tag_name)
            if tag_id and tag_id in exif:
                try:
                    return datetime.strptime(exif[tag_id], "%Y:%m:%d %H:%M:%S")
                except (ValueError, TypeError):
                    continue
    except Exception:
        pass
    return None


def get_image_date(path: Path) -> datetime | None:
    """
    Returns the best available date for an image file.
    Returns None if the file is corrupted or completely unreadable.
    Priority: EXIF DateTimeOriginal → DateTimeDigitized → DateTime → file mtime
    """
    try:
        with Image.open(path) as img:
            img.load()  # force full decode — raises on corrupted files
            dt = _exif_date(img)
    except Exception:
        return None  # corrupted or unsupported format

    if dt:
        return dt

    # Fall back to filesystem modification time
    try:
        return datetime.fromtimestamp(path.stat().st_mtime)
    except Exception:
        return None


def scan_folders(paths: list[str]) -> tuple[list[dict], int]:
    """
    Recursively scans one or more folders for images.

    Returns:
        images  — list of dicts, sorted newest-first, each with:
                  path, filename, date (datetime), date_str
        corrupted — count of files that could not be read
    """
    images: list[dict] = []
    corrupted = 0

    for folder_str in paths:
        folder = Path(folder_str.strip())
        if not folder.is_dir():
            continue
        for f in folder.rglob("*"):
            if f.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            dt = get_image_date(f)
            if dt is None:
                corrupted += 1
                continue
            images.append({
                "path": str(f),
                "filename": f.name,
                "date": dt,
                "date_str": dt.strftime("%Y-%m-%d  %H:%M"),
            })

    images.sort(key=lambda x: x["date"], reverse=True)
    return images, corrupted


def compute_stats(images: list[dict]) -> dict:
    """
    Computes summary statistics for a loaded image set.

    Returns a dict with overall span stats and a per-year breakdown.
    Missing days per year = total calendar days in that year − unique days with images.
    """
    if not images:
        return {}

    dates = [img["date"].date() for img in images]
    min_date = min(dates)
    max_date = max(dates)
    total_span_days = (max_date - min_date).days + 1
    days_with_images = len(set(dates))

    # Build per-year data
    year_data: dict[int, dict] = {}
    for img in images:
        y = img["date"].year
        if y not in year_data:
            year_data[y] = {"images": 0, "days": set()}
        year_data[y]["images"] += 1
        year_data[y]["days"].add(img["date"].date())

    per_year: dict[int, dict] = {}
    for y, data in sorted(year_data.items(), reverse=True):
        total_year_days = 366 if isleap(y) else 365
        days_covered = len(data["days"])
        per_year[y] = {
            "images": data["images"],
            "days_with_images": days_covered,
            "total_year_days": total_year_days,
            "missing_days": total_year_days - days_covered,
            "coverage_pct": round(days_covered / total_year_days * 100),
        }

    return {
        "total": len(images),
        "min_date": min_date,
        "max_date": max_date,
        "total_span_days": total_span_days,
        "days_with_images": days_with_images,
        "missing_days": total_span_days - days_with_images,
        "per_year": per_year,
    }
