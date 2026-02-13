"""Cover image generation using OpenAI Images API."""

import os
import logging
import base64
from typing import Optional
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Generate cover images using OpenAI."""
    
    def __init__(self, api_key: str):
        """Initialize image generator.
        
        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
    
    def generate_cover(
        self,
        article_title: str,
        summary: str,
        style: str = "clean editorial",
        language: str = "zh-CN"
    ) -> Optional[bytes]:
        """Generate a cover image from article title and summary.
        
        Args:
            article_title: Article title
            summary: Article summary
            style: Image style (default "clean editorial")
            language: Content language
            
        Returns:
            PNG image bytes or None if failed
        """
        # Build prompt
        prompt = self._build_image_prompt(
            article_title,
            summary,
            style,
            language
        )
        
        try:
            response = requests.post(
                f"{self.base_url}/images/generations",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": prompt,
                    "model": "dall-e-3",
                    "n": 1,
                    "size": "1200x628",
                    "quality": "standard",
                    "style": "natural"
                },
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            image_url = result["data"][0]["url"]
            
            # Fetch the image
            img_response = requests.get(image_url, timeout=30)
            img_response.raise_for_status()
            
            logger.info(f"Generated cover image for '{article_title}'")
            return img_response.content
            
        except requests.RequestException as e:
            logger.error(f"Image generation failed: {e}")
            return None
    
    def _build_image_prompt(
        self,
        title: str,
        summary: str,
        style: str,
        language: str
    ) -> str:
        """Build image generation prompt."""
        # Create a concise visual description
        keywords = title.split()[:5]  # First 5 words
        
        if language == "zh-CN":
            prompt = (
                f"Professional article cover image. \n"
                f"Title: {title}\n"
                f"Style: {style}, modern, high-quality.\n"
                f"Colors: Professional blues, whites, accent colors.\n"
                f"Layout: Clean background with subtle design elements.\n"
                f"Suitable for blog/news article cover.\n"
                f"No text overlays, 1200x628px aspect ratio."
            )
        else:
            prompt = (
                f"Professional article cover. {style} design.\n"
                f"Topic: {title}\n"
                f"Colors: Professional color scheme, modern.\n"
                f"Clear, visually appealing background.\n"
                f"1200x628px landscape. No text."
            )
        
        return prompt
    
    @staticmethod
    def save_image(image_bytes: bytes, path: Path) -> bool:
        """Save image to file.
        
        Args:
            image_bytes: Image binary data
            path: Output file path
            
        Returns:
            True if saved successfully
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                f.write(image_bytes)
            logger.info(f"Saved image to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            return False
