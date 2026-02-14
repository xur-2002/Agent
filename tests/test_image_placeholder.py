"""Test that provide_cover_image writes placeholder when material has sources (Rule 2)."""
from pathlib import Path
import tempfile
from agent.image_provider import provide_cover_image


def test_image_placeholder_with_sources():
    """Test Rule 2: material with sources -> write placeholder PNG and return ok."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Case 1: material with non-empty sources list
        material = {'sources': [{'title': 'News', 'url': 'http://example.com'}]}
        info = provide_cover_image(material, tmpdir, 'test-slug-1')
        
        assert info['image_status'] == 'ok', f"Expected ok, got {info}"
        assert 'image_path' in info
        assert 'image_relpath' in info
        assert Path(info['image_path']).exists(), f"Image file not written at {info['image_path']}"


def test_image_placeholder_empty_dict():
    """Test Rule 2: empty dict (no sources key) -> write placeholder PNG and return ok."""
    with tempfile.TemporaryDirectory() as tmpdir:
        material = {}
        info = provide_cover_image(material, tmpdir, 'test-slug-2')
        
        assert info['image_status'] == 'ok'
        assert 'image_path' in info
        assert Path(info['image_path']).exists()


def test_image_placeholder_none_material():
    """Test Rule 2: None material -> write placeholder PNG and return ok."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # None is not a dict, so fall through to Rule 2
        material = None
        info = provide_cover_image(material, tmpdir, 'test-slug-3')
        
        assert info['image_status'] == 'ok'
        assert 'image_path' in info
        assert Path(info['image_path']).exists()
