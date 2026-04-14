from unittest.mock import MagicMock, patch

from app.core.email import send_reset_email


def test_send_reset_email_connects_and_sends(monkeypatch):
    """Verify SMTP STARTTLS flow: connect → starttls → login → send_message."""
    mock_smtp_instance = MagicMock()
    mock_smtp_class = MagicMock(return_value=mock_smtp_instance)
    mock_smtp_instance.__enter__ = MagicMock(return_value=mock_smtp_instance)
    mock_smtp_instance.__exit__ = MagicMock(return_value=False)

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "bot@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.com")

    with patch("smtplib.SMTP", mock_smtp_class):
        send_reset_email("athlete@test.com", "https://app.example.com/reset?token=abc123")

    mock_smtp_class.assert_called_once_with("smtp.example.com", 587)
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once_with("bot@example.com", "secret")
    mock_smtp_instance.send_message.assert_called_once()
    # Verify recipient in the message
    sent_msg = mock_smtp_instance.send_message.call_args[0][0]
    assert sent_msg["To"] == "athlete@test.com"
    assert "https://app.example.com/reset?token=abc123" in sent_msg.get_payload()
