from agent.email_sender import send_daily_summary


def test_email_skip(monkeypatch):
    # Ensure SMTP env not set
    monkeypatch.delenv('SMTP_HOST', raising=False)
    monkeypatch.delenv('SMTP_USERNAME', raising=False)
    monkeypatch.delenv('SMTP_PASSWORD', raising=False)

    res = send_daily_summary('subj', '<p>body</p>', attachments=None, to_addr='xu.r@wustl.edu')
    assert res['status'] == 'skipped'
