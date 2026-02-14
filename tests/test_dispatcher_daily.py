"""Test that dispatcher correctly routes daily_content_batch task."""
from agent.models import Task, TaskResult
from agent.task_runner import run_task


def test_dispatcher_daily_content_batch(monkeypatch):
    """Test that run_task dispatches daily_content_batch without 'Unknown task ID' error."""
    # Mock external calls to avoid real API calls
    monkeypatch.setenv('TRENDS_GEO', 'US')
    
    # Mock select_topics to return empty list (safe for testing)
    def mock_select_topics(*args, **kwargs):
        return []
    
    monkeypatch.setattr('agent.task_runner.select_topics', mock_select_topics)
    
    # Mock send_article_generation_results to avoid Feishu webhook call
    def mock_send_feishu(*args, **kwargs):
        pass
    
    monkeypatch.setattr('agent.task_runner.send_article_generation_results', mock_send_feishu)
    
    # Create task with daily_content_batch ID
    task = Task(
        id='daily_content_batch',
        params={
            'daily_quota': 2,
            'seed_keywords': ['test'],
            'email_to': 'test@example.com'
        }
    )
    
    # Run task - should NOT raise "Unknown task ID: daily_content_batch"
    try:
        result = run_task(task)
        assert isinstance(result, TaskResult)
        assert result.status in ['success', 'failed', 'skipped']
        assert 'duration_sec' in dir(result)
    except ValueError as e:
        if 'Unknown task ID' in str(e):
            raise AssertionError(f"Dispatcher did not route daily_content_batch: {e}")
        raise
