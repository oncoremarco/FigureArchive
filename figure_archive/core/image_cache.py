import hashlib
import shutil
from pathlib import Path


THUMB_SIZE = (256, 256)


def _cache_dir() -> Path:
    from figure_archive.db.connection import current_path
    p = current_path()
    base = Path(p).parent if p else _fallback_dir()
    d = base / "image_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _thumb_dir() -> Path:
    d = _cache_dir() / "thumbs"
    d.mkdir(exist_ok=True)
    return d


def _fallback_dir() -> Path:
    from figure_archive.core.config import app_data_dir
    return app_data_dir()


def _ext_from_content_type(ct: str) -> str:
    ct = ct.lower().split(";")[0].strip()
    return {"image/jpeg": ".jpg", "image/png": ".png",
            "image/gif": ".gif", "image/webp": ".webp"}.get(ct, ".jpg")


def _make_thumbnail(src: Path, thumb_path: Path) -> None:
    from PIL import Image
    with Image.open(src) as img:
        img.thumbnail(THUMB_SIZE, Image.LANCZOS)
        img.convert("RGB").save(thumb_path, "JPEG", quality=85)


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _path_hash(p: Path) -> str:
    return hashlib.md5(str(p).encode()).hexdigest()


def _ensure_thumb(src: Path, name: str) -> Path | None:
    thumb = _thumb_dir() / f"{name}.jpg"
    if not thumb.exists() and src.exists():
        try:
            _make_thumbnail(src, thumb)
        except Exception as exc:
            print(f"[image_cache] thumb failed {src}: {exc}")
            return None
    return thumb if thumb.exists() else None


def cache_image_from_url(url: str) -> Path | None:
    """Download and cache a URL image; return local path or None."""
    import requests
    h = _url_hash(url)
    cache = _cache_dir()
    for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        existing = cache / f"{h}{ext}"
        if existing.exists():
            _ensure_thumb(existing, h)
            return existing
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        ext = _ext_from_content_type(resp.headers.get("content-type", "image/jpeg"))
        dest = cache / f"{h}{ext}"
        dest.write_bytes(resp.content)
        _ensure_thumb(dest, h)
        return dest
    except Exception as exc:
        print(f"[image_cache] download failed {url}: {exc}")
        return None


def cache_image_from_file(src_path: Path | str, item_id: str) -> Path | None:
    """Copy a file into the personal photos folder; return dest path or None."""
    import uuid
    src = Path(src_path)
    if not src.exists():
        return None
    from figure_archive.db.connection import current_path
    db_p = current_path()
    photos_dir = (Path(db_p).parent if db_p else _fallback_dir()) / "photos" / item_id
    photos_dir.mkdir(parents=True, exist_ok=True)
    dest = photos_dir / f"{uuid.uuid4().hex}{src.suffix.lower() or '.jpg'}"
    shutil.copy2(src, dest)
    _ensure_thumb(dest, _path_hash(dest))
    return dest


def get_thumbnail_path(local_path: str | Path) -> Path | None:
    """Return 256×256 thumbnail path for a cached/personal image, or None."""
    p = Path(local_path)
    thumb = _ensure_thumb(p, _path_hash(p))
    return thumb
