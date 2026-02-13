"""Simple image provider: extract image urls from sources or try a simple lookup and download.

This is intentionally lightweight: failures must not raise, only return status.
"""
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import requests

logger = logging.getLogger(__name__)


def download_image(url: str, dest: Path, timeout: int = 10) -> bool:
    try:
        resp = requests.get(url, timeout=timeout, stream=True)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, 'wb') as f:
            for chunk in resp.iter_content(1024 * 8):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        logger.warning(f"Failed to download image {url}: {e}")
        return False


def provide_cover_image(material_pack: Dict[str, Any], output_dir: str, slug: str) -> Dict[str, Any]:
    """Attempt to find and download a cover image.

    Returns dict with image_status, image_path (or None), image_source_url, image_credit, reason
    """
    out = {
        'image_status': 'skipped',
        'image_path': None,
        'image_source_url': None,
        'image_credit': None,
        'reason': 'no_image_found'
    }
    # Try to get image from material sources if any
    sources = material_pack.get('sources', []) or []
    for s in sources:
        img = s.get('image') or s.get('thumbnail') or s.get('image_url')
        if img:
            dest = Path(output_dir) / slug / 'images' / 'cover.jpg'
            ok = download_image(img, dest)
            if ok:
                out.update({'image_status': 'ok', 'image_path': str(dest), 'image_source_url': img, 'image_credit': s.get('title')})
                return out

    # No image found in sources - simple fallback: return skipped
    out['reason'] = 'no_image_candidate'
    return out
