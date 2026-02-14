"""Image placeholder provider for articles.

Provides a stable local placeholder image that never depends on external APIs.
"""
import base64
import shutil
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# 1x1 PNG transparent pixel base64 (fallback bytes)
_MIN_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="


def provide_cover_image(material: dict, base_output: str, slug: str) -> dict:
    """
    Provide a cover image for an article.
    
    **RULES:**
    - If material is a dict AND 'sources' key exists AND sources == []: return skipped (no file written)
    - Otherwise: always write placeholder PNG and return ok
    - Only return failed if disk write fails
    
    Args:
        material: Material pack dict (may be {}, None, or have 'sources' key)
        base_output: Path to output directory (will create images/ subdir)
        slug: Article slug for filename (becomes images/<slug>.png)
    
    Returns:
        dict with keys:
        - image_status: "ok" | "skipped" | "failed"
        - image_path: str(absolute_path) or None
        - image_relpath: str (e.g., "images/<slug>.png") or None
        - reason: str (optional explanation)
    """
    # Rule 1: Check if material has empty sources list - return skipped WITHOUT writing
    if isinstance(material, dict) and "sources" in material and material["sources"] == []:
        return {
            "image_status": "skipped",
            "reason": "no_sources",
            "image_path": None,
            "image_relpath": None
        }
    
    # Rule 2: Otherwise always write placeholder
    try:
        base = Path(base_output)
        images_dir = base / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        dest = images_dir / f"{slug}.png"

        # Try A: copy assets/placeholder.png if exists
        wrote = False
        try:
            repo_root = Path(__file__).resolve().parents[1]
            asset = repo_root / "assets" / "placeholder.png"
            if asset.exists() and asset.is_file():
                shutil.copyfile(asset, dest)
                wrote = True
        except Exception as e_copy:
            logger.debug(f"Could not copy assets/placeholder.png: {e_copy}, trying fallback")

        # Try B: write minimal PNG bytes (fallback)
        if not wrote:
            try:
                data = base64.b64decode(_MIN_PNG_B64)
                with open(dest, "wb") as f:
                    f.write(data)
                wrote = True
            except Exception as e_write:
                logger.error(f"Failed to write placeholder PNG: {e_write}")
                return {
                    "image_status": "failed",
                    "image_path": str(dest),
                    "image_relpath": f"images/{slug}.png",
                    "reason": f"disk_write_failed: {str(e_write)[:100]}"
                }

        # Verify file exists
        if dest.exists():
            rel = Path("images") / f"{slug}.png"
            return {
                "image_status": "ok",
                "image_path": str(dest),
                "image_relpath": str(rel)
            }
        else:
            return {
                "image_status": "failed",
                "image_path": str(dest),
                "image_relpath": f"images/{slug}.png",
                "reason": "file_not_written"
            }

    except Exception as e:
        logger.error(f"provide_cover_image fatal error: {e}")
        return {
            "image_status": "failed",
            "reason": f"unexpected_error: {str(e)[:100]}"
        }
