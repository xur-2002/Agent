"""Image provider for articles with image search and fallback to placeholder.

Provides:
- image_search(topic): Find images with metadata
- provide_cover_image(material, base_output, slug): Get cover image with fallback
"""
import base64
import shutil
import requests
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 1x1 PNG transparent pixel base64 (fallback bytes)
_MIN_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="


def image_search(topic: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Search for images using Bing Image Search API.
    
    Args:
        topic: Search query/keyword
        limit: Max number of results (default 3)
        
    Returns:
        List of image dicts with:
        - url: image URL
        - source_url: page URL
        - title: image title
        - site_name: hosting site
        - license_note: license info or source attribution
        
    Returns empty list if search fails or not configured
    """
    from agent.config import Config
    
    # Try Bing Image Search if configured
    bing_key = Config.BING_SEARCH_SUBSCRIPTION_KEY.strip()
    if bing_key:
        try:
            # Bing Image Search API
            search_url = "https://api.bing.microsoft.com/v7.0/images/search"
            headers = {"Ocp-Apim-Subscription-Key": bing_key}
            params = {
                "q": topic,
                "count": limit,
                "offset": 0,
                "mkt": "en-US"
            }
            
            logger.debug(f"Searching images for '{topic}' using Bing API")
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            images = []
            for img in data.get("value", [])[:limit]:
                images.append({
                    'url': img.get('contentUrl', ''),
                    'source_url': img.get('hostPageUrl', ''),
                    'title': img.get('name', ''),
                    'site_name': img.get('hostPageDisplayUrl', '').split('/')[0] if img.get('hostPageDisplayUrl') else 'Unknown',
                    'license_note': f"Image from {img.get('hostPageDisplayUrl', topic).split('/')[0]} - source link provided"
                })
            return images
        except Exception as e:
            logger.warning(f"Bing image search failed for '{topic}': {e}")
    
    # Try Unsplash API (free, no key)
    try:
        logger.debug(f"Searching images for '{topic}' using Unsplash API")
        url = "https://api.unsplash.com/search/photos"
        headers = {"Accept-Version": "v1"}
        params = {"query": topic, "per_page": limit}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            images = []
            for photo in data.get("results", [])[:limit]:
                images.append({
                    'url': photo.get('urls', {}).get('regular', ''),
                    'source_url': photo.get('links', {}).get('html', ''),
                    'title': photo.get('description') or photo.get('alt_description', ''),
                    'site_name': 'Unsplash',
                    'license_note': f"Photo by {photo.get('user', {}).get('name', 'Unknown')} on Unsplash - CC0 License"
                })
            return images
    except Exception as e:
        logger.debug(f"Unsplash image search failed: {e}")
    
    logger.warning(f"No image search provider available for topic '{topic}'")
    return []


def download_image(image_url: str, dest_path: Path, timeout: int = 10) -> bool:
    """Download image from URL to local file.
    
    Args:
        image_url: URL of image
        dest_path: Destination file path
        timeout: Request timeout in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.debug(f"Downloading image from {image_url[:80]}")
        response = requests.get(image_url, timeout=timeout, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        with open(dest_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Image downloaded to {dest_path}")
        return True
    except Exception as e:
        logger.warning(f"Failed to download image: {e}")
        return False


def provide_cover_image(material: dict, base_output: str, slug: str) -> dict:
    """
    Provide a cover image for an article.
    
    STRATEGY:
    1. Try to search for real images (if not skipped)
    2. Try to download the best image
    3. Fallback to placeholder PNG
    
    Args:
        material: Material pack dict with 'sources' list
        base_output: Path to output directory
        slug: Article slug for filename
    
    Returns:
        dict with:
        - image_status: "ok" | "skipped" | "failed"
        - image_path: absolute file path (if ok/failed)
        - image_relpath: relative path (e.g., "images/slug.png")
        - image_url: original URL (if real image)
        - source_url: page URL (if real image)
        - site_name: hosting site (if real image)
        - license_note: attribution text
        - reason: skip/error reason (if skipped/failed)
    """
    base = Path(base_output)
    images_dir = base / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    dest = images_dir / f"{slug}.png"
    
    # Check if should skip (Rule 1: empty sources)
    sources = material.get('sources', [])
    if isinstance(sources, list) and len(sources) == 0:
        logger.info(f"Skipping image for '{slug}' (no sources)")
        return {
            "image_status": "skipped",
            "reason": "no_sources",
            "image_path": None,
            "image_relpath": f"images/{slug}.png"
        }
    
    # Try to search and download real image
    try:
        topic = material.get('topic') or slug
        images = image_search(topic, limit=1)
        
        if images:
            img = images[0]
            if download_image(img.get('url'), dest):
                return {
                    "image_status": "ok",
                    "image_path": str(dest),
                    "image_relpath": f"images/{slug}.png",
                    "image_url": img.get('url'),
                    "source_url": img.get('source_url'),
                    "site_name": img.get('site_name'),
                    "license_note": img.get('license_note'),
                    "image_source": "real_search"
                }
    except Exception as e:
        logger.warning(f"Image search/download failed for '{topic}': {e}, falling back to placeholder")
    
    # Fallback to placeholder
    try:
        wrote = False
        
        # Try copy from assets
        try:
            repo_root = Path(__file__).resolve().parents[1]
            asset = repo_root / "assets" / "placeholder.png"
            if asset.exists() and asset.is_file():
                shutil.copyfile(asset, dest)
                wrote = True
                logger.debug(f"Copied placeholder from assets to {dest}")
        except Exception as e:
            logger.debug(f"Could not copy assets/placeholder.png: {e}")
        
        # Fallback: write minimal PNG
        if not wrote:
            try:
                data = base64.b64decode(_MIN_PNG_B64)
                with open(dest, "wb") as f:
                    f.write(data)
                wrote = True
                logger.debug(f"Wrote base64 placeholder to {dest}")
            except Exception as e:
                logger.error(f"Failed to write placeholder PNG: {e}")
        
        if dest.exists():
            return {
                "image_status": "ok",
                "image_path": str(dest),
                "image_relpath": f"images/{slug}.png",
                "image_source": "placeholder",
                "license_note": "Placeholder image"
            }
        else:
            return {
                "image_status": "failed",
                "reason": "placeholder_write_failed",
                "image_path": str(dest),
                "image_relpath": f"images/{slug}.png"
            }
    
    except Exception as e:
        logger.error(f"Unexpected error in provide_cover_image: {e}")
        return {
            "image_status": "failed",
            "reason": f"unexpected_error: {str(e)[:100]}",
            "image_relpath": f"images/{slug}.png"
        }

