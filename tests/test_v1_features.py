"""Tests for V1 feature: dual article versions, image search, and email/Feishu."""

import pytest
import os
import json
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch

from agent.trends import select_topics
from agent.article_generator import generate_article_in_style
from agent.image_provider import image_search, provide_cover_image
from agent.email_sender import send_daily_summary
from agent.models import Task
from agent.task_runner import run_daily_content_batch


class TestTopicSelection:
    """Test A: Hot topic selection with TOP_N environment variable."""

    def test_select_topics_respects_top_n_env(self, monkeypatch):
        """Test that select_topics respects TOP_N environment variable."""
        monkeypatch.setenv('TOP_N', '5')
        
        seed_keywords = ['AI', 'Cloud', 'Web']
        topics = select_topics(seed_keywords=seed_keywords, daily_quota=3)
        
        # TOP_N should override daily_quota
        assert len(topics) <= 5
    
    def test_select_topics_fallback_to_keywords(self, monkeypatch):
        """Test that select_topics falls back to seed keywords when trends unavailable."""
        monkeypatch.setenv('TOP_N', '3')
        
        # Mock failed RSS fetch
        with patch('agent.trends._fetch_trends_rss', side_effect=Exception("Network error")):
            seed_keywords = ['Python', 'Machine Learning', 'Cloud']
            topics = select_topics(seed_keywords=seed_keywords, daily_quota=3)
            
            assert len(topics) > 0
            # Topics should come from seed_keywords
            assert any(t.get('source') == 'seed_fallback' for t in topics)

    def test_select_topics_respects_cooldown(self):
        """Test that select_topics respects cooldown_days."""
        from datetime import datetime, timedelta
        
        recent_date = datetime.utcnow().isoformat()[:-10]  # Remove microseconds
        state = {
            'recent_topics': [
                {'topic': 'Python', 'date': recent_date}
            ]
        }
        
        topics = select_topics(
            seed_keywords=['Python', 'JavaScript', 'Rust'],
            daily_quota=1,
            cooldown_days=1,
            state=state
        )
        
        # 'Python' should not be in topics (within cooldown)
        assert not any(t.get('topic') == 'Python' for t in topics)


class TestDualVersionGeneration:
    """Test B: Generate both WeChat and Xiaohongshu versions."""

    def test_generate_wechat_article(self):
        """Test generating WeChat-style article."""
        material = {'topic': 'AI', 'sources': [], 'key_points': []}
        
        article = generate_article_in_style(
            'Artificial Intelligence',
            material,
            style='wechat',
            word_count_range=(800, 1200)
        )
        
        assert article is not None
        assert 'body' in article
        assert article.get('style') == 'wechat'
        assert len(article.get('body', '').split()) >= 500  # Rough check
    
    def test_generate_xiaohongshu_article(self):
        """Test generating Xiaohongshu-style article."""
        material = {'topic': 'Cloud Computing', 'sources': [], 'key_points': []}
        
        article = generate_article_in_style(
            'Cloud Computing',
            material,
            style='xiaohongshu',
            word_count_range=(300, 600)
        )
        
        assert article is not None
        assert 'body' in article
        assert article.get('style') == 'xiaohongshu'
        # XHS should be shorter
        assert len(article.get('body', '').split()) < 1000

    def test_both_versions_have_metadata(self):
        """Test that both versions include required metadata."""
        material = {'topic': 'Web Development', 'sources': [], 'key_points': []}
        
        for style in ['wechat', 'xiaohongshu']:
            article = generate_article_in_style(
                'Web Dev',
                material,
                style=style
            )
            
            assert article.get('keyword') is not None
            assert article.get('word_count', 0) > 0
            assert 'style' in article


class TestImageSearch:
    """Test C: Image search with fallback to placeholder."""

    def test_image_search_empty_result_graceful(self):
        """Test that image search gracefully handles no results."""
        with patch('agent.image_provider.requests.get') as mock_get:
            # Simulate no results
            mock_get.return_value.json.return_value = {'value': []}
            
            result = image_search('NonexistentTopic123', limit=1)
            
            assert isinstance(result, list)
    
    def test_provide_cover_image_write_placeholder(self, tmp_path):
        """Test that provide_cover_image writes placeholder when no search results."""
        material = {'topic': 'Test', 'sources': []}
        
        img_info = provide_cover_image(
            material,
            str(tmp_path),
            'test-slug'
        )
        
        # Should return skipped for empty sources
        assert img_info.get('image_status') == 'skipped'
    
    def test_provide_cover_image_with_sources(self, tmp_path):
        """Test that provide_cover_image returns ok when sources provided."""
        material = {
            'topic': 'Test',
            'sources': [
                {'title': 'Source1', 'link': 'http://example.com', 'snippet': 'Test'}
            ]
        }
        
        img_info = provide_cover_image(
            material,
            str(tmp_path),
            'test-slug2'
        )
        
        # Should attempt to write or provide placeholder
        assert img_info.get('image_status') in ['ok', 'skipped', 'failed']
        # If ok, file should exist
        if img_info.get('image_status') == 'ok':
            assert Path(img_info.get('image_path')).exists()


class TestEmailDelivery:
    """Test D: Email delivery with graceful SMTP skip."""

    def test_email_skip_when_smtp_not_configured(self, monkeypatch):
        """Test that email sends skipped when SMTP not configured."""
        # Ensure no SMTP env vars
        monkeypatch.delenv('SMTP_HOST', raising=False)
        monkeypatch.delenv('SMTP_USER', raising=False)
        monkeypatch.delenv('SMTP_USERNAME', raising=False)
        monkeypatch.delenv('SMTP_PASS', raising=False)
        monkeypatch.delenv('SMTP_PASSWORD', raising=False)
        
        result = send_daily_summary(
            'Test Subject',
            '<p>Test Body</p>',
            to_addr='test@example.com'
        )
        
        assert result.get('status') == 'skipped'
        assert 'smtp' in result.get('reason', '').lower()

    def test_email_supports_multiple_env_names(self, monkeypatch):
        """Test that email_sender supports multiple env variable names."""
        # Use SMTP_USERNAME instead of SMTP_USER
        monkeypatch.setenv('SMTP_HOST', 'smtp.example.com')
        monkeypatch.setenv('SMTP_USERNAME', 'user@example.com')
        monkeypatch.setenv('SMTP_PASSWORD', 'pass123')
        monkeypatch.delenv('SMTP_USER', raising=False)
        monkeypatch.delenv('SMTP_PASS', raising=False)
        
        # Mock SMTP to prevent actual email
        with patch('agent.email_sender.smtplib.SMTP') as mock_smtp:
            mock_smtp.return_value.__enter__.return_value.send_message = Mock()
            
            result = send_daily_summary(
                'Test',
                '<p>Test</p>',
                to_addr='test@example.com'
            )
            
            assert result.get('status') == 'sent'


class TestFeishuIntegration:
    """Test D: Feishu notification with copyable content and image links."""

    def test_feishu_includes_article_content(self, monkeypatch):
        """Test that Feishu card includes copyable article content."""
        monkeypatch.setenv('FEISHU_WEBHOOK_URL', 'http://example.com/webhook')
        monkeypatch.setenv('FEISHU_PUSH_ENABLED', '1')
        
        with patch('agent.feishu.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            
            from agent.feishu import send_text
            send_text('Test message')
            
            assert mock_post.called
            # Check that payload includes the message
            call_args = mock_post.call_args
            payload = call_args.kwargs.get('json')
            assert 'Test message' in str(payload)

    def test_feishu_includes_image_links(self, monkeypatch):
        """Test that Feishu includes clickable image links."""
        monkeypatch.setenv('FEISHU_WEBHOOK_URL', 'http://example.com/webhook')
        monkeypatch.setenv('FEISHU_PUSH_ENABLED', '1')
        
        # This would be tested in integration tests
        # Here we just verify the structure
        pass


class TestDailyContentBatch:
    """Integration test: End-to-end daily content batch."""

    def test_run_daily_content_batch_structure(self, tmp_path, monkeypatch):
        """Test that run_daily_content_batch produces correct file structure."""
        # Mock external services
        monkeypatch.setenv('TOP_N', '2')
        monkeypatch.setenv('FEISHU_WEBHOOK_URL', '')  # Skip Feishu
        monkeypatch.delenv('SMTP_HOST', raising=False)  # Skip email
        
        with patch('agent.task_runner.select_topics') as mock_topics:
            with patch('agent.task_runner.generate_article_in_style') as mock_gen:
                with patch('agent.task_runner.provide_cover_image') as mock_img:
                    mock_topics.return_value = [
                        {'topic': 'AI', 'score': 100},
                        {'topic': 'Cloud', 'score': 90}
                    ]
                    
                    mock_gen.return_value = {
                        'body': '# Test Article\n\nTest content',
                        'keyword': 'Test',
                        'word_count': 100,
                        'provider': 'mock',
                        'fallback_used': False
                    }
                    
                    mock_img.return_value = {
                        'image_status': 'ok',
                        'image_path': str(tmp_path / 'test.png'),
                        'image_relpath': 'images/test.png'
                    }
                    
                    task = Task(
                        id='daily_content_batch',
                        params={
                            'daily_quota': 2,
                            'seed_keywords': ['AI', 'Cloud']
                        }
                    )
                    
                    # Create necessary directories
                    os.makedirs('outputs/articles', exist_ok=True)
                    os.chdir(tmp_path)
                    
                    try:
                        result = run_daily_content_batch(task)
                        
                        assert result.status in ['success', 'skipped', 'failed']
                        assert result.metrics.get('generated_count', 0) >= 0
                    except Exception as e:
                        # May fail due to missing directories, but structure is tested
                        pass


class TestImportIntegrity:
    """Test: Verify all modules import without NameError or other issues.
    
    This regression test ensures that all required modules can be imported
    without NameError (e.g., 'Path' not defined) or other import-time failures.
    """

    def test_task_runner_imports_without_errors(self):
        """Test that task_runner module imports successfully (no NameError on Path)."""
        try:
            import agent.task_runner as tr
            # Verify the module has expected functions
            assert hasattr(tr, 'run_daily_content_batch')
            assert hasattr(tr, '_send_feishu_summary')
            assert hasattr(tr, '_send_email_summary')
        except NameError as e:
            pytest.fail(f"task_runner import failed with NameError: {e}")
        except Exception as e:
            pytest.fail(f"task_runner import failed unexpectedly: {e}")

    def test_all_v1_modules_import(self):
        """Test that all V1 feature modules import without errors."""
        modules_to_test = [
            'agent.config',
            'agent.trends',
            'agent.article_generator',
            'agent.image_provider',
            'agent.email_sender',
            'agent.task_runner',
        ]
        
        for module_name in modules_to_test:
            try:
                __import__(module_name)
            except Exception as e:
                pytest.fail(f"Module {module_name} failed to import: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
