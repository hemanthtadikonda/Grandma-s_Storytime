"""Search and download scene images per job; files live in a temp dir and are deleted after render."""

import logging
import re
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from PIL import Image

from storytime_common.settings import Settings

logger = logging.getLogger(__name__)

USER_AGENT = "GrandmasStorytime/0.1 (kids educational shorts; contact: local)"


def fetch_scene_images(script: dict[str, Any], out_dir: Path, settings: Settings) -> list[Path | None]:
    if settings.image_provider == "none":
        return [None] * len(script["scenes"])

    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path | None] = []
    used_urls: set[str] = set()

    for i, scene in enumerate(script["scenes"]):
        if scene.get("skip_image_search"):
            paths.append(None)
            continue
        query = scene.get("image_query") or scene.get("caption") or "children illustration"
        path = out_dir / f"scene_{i:02d}.jpg"
        try:
            url = _search_image_url(query, settings, used_urls)
            if url and _download_and_prepare(url, path, settings):
                used_urls.add(url)
                paths.append(path)
                logger.info("scene %s image: %s", i, query)
            else:
                paths.append(None)
        except Exception as exc:  # noqa: BLE001 — per-scene fallback to generated art
            logger.warning("scene %s image failed (%s): %s", i, query, exc)
            paths.append(None)

    return paths


def _search_image_url(query: str, settings: Settings, used_urls: set[str]) -> str | None:
    if settings.image_provider == "wikimedia":
        return _wikimedia_url(query, settings, used_urls)
    if settings.image_provider == "pexels":
        return _pexels_url(query, settings, used_urls)
    if settings.image_provider == "pixabay":
        return _pixabay_url(query, settings, used_urls)
    raise ValueError(f"Unknown IMAGE_PROVIDER={settings.image_provider}")


def _http_get(url: str, settings: Settings, headers: dict[str, str] | None = None) -> requests.Response:
    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    resp = requests.get(url, headers=hdrs, timeout=settings.image_search_timeout_sec)
    resp.raise_for_status()
    return resp


def _wikimedia_url(query: str, settings: Settings, used_urls: set[str]) -> str | None:
    safe = quote(query[:120])
    api = (
        "https://commons.wikimedia.org/w/api.php"
        f"?action=query&generator=search&gsrsearch={safe}&gsrnamespace=6"
        "&gsrlimit=8&prop=imageinfo&iiprop=url&iiurlwidth=1200&format=json"
    )
    data = _http_get(api, settings).json()
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        url = infos[0].get("thumburl") or infos[0].get("url")
        if not url or url in used_urls:
            continue
        if not re.search(r"\.(jpg|jpeg|png|webp)($|\?)", url, re.I):
            continue
        return url
    return None


def _pexels_url(query: str, settings: Settings, used_urls: set[str]) -> str | None:
    if not settings.pexels_api_key:
        raise ValueError("PEXELS_API_KEY is required when IMAGE_PROVIDER=pexels")
    resp = _http_get(
        f"https://api.pexels.com/v1/search?query={quote(query)}&per_page=5&orientation=portrait",
        settings,
        headers={"Authorization": settings.pexels_api_key},
    )
    for photo in resp.json().get("photos", []):
        url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large")
        if url and url not in used_urls:
            return url
    return None


def _pixabay_url(query: str, settings: Settings, used_urls: set[str]) -> str | None:
    if not settings.pixabay_api_key:
        raise ValueError("PIXABAY_API_KEY is required when IMAGE_PROVIDER=pixabay")
    resp = _http_get(
        "https://pixabay.com/api/"
        f"?key={settings.pixabay_api_key}&q={quote(query)}&image_type=photo"
        "&orientation=vertical&per_page=8&safesearch=true",
        settings,
    )
    for hit in resp.json().get("hits", []):
        url = hit.get("largeImageURL") or hit.get("webformatURL")
        if url and url not in used_urls:
            return url
    return None


def _download_and_prepare(url: str, dest: Path, settings: Settings) -> bool:
    resp = _http_get(url, settings)
    if len(resp.content) > settings.image_max_bytes:
        return False
    img = Image.open(BytesIO(resp.content)).convert("RGB")
    img = _cover_crop_vertical(img, settings.image_target_width, settings.image_target_height)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=88)
    return True


def _cover_crop_vertical(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    w, h = img.size
    scale = max(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))
