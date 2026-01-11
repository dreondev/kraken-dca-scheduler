"""Tests for ntfy notification client."""

import pytest
from unittest.mock import Mock, patch
from src.notifications.ntfy import NtfyNotifier, NotificationError
import requests


@pytest.fixture
def notifier():
    """Create ntfy notifier instance."""
    return NtfyNotifier(
        server="https://ntfy.sh",
        topic="test-topic",
        priority="default",
        timeout=10,
    )


class TestNtfyNotifierInit:
    """Tests for NtfyNotifier initialization."""
    
    def test_init_basic(self):
        """Test basic initialization."""
        notifier = NtfyNotifier(topic="test-topic")
        
        assert notifier._topic == "test-topic"
        assert notifier._server == "https://ntfy.sh"
        assert notifier._priority == "default"
        assert notifier._url == "https://ntfy.sh/test-topic"
    
    def test_init_custom_server(self):
        """Test initialization with custom server."""
        notifier = NtfyNotifier(
            server="https://custom.ntfy.sh",
            topic="test-topic"
        )
        
        assert notifier._url == "https://custom.ntfy.sh/test-topic"
    
    def test_init_server_trailing_slash(self):
        """Test that trailing slash is removed from server URL."""
        notifier = NtfyNotifier(
            server="https://ntfy.sh/",
            topic="test-topic"
        )
        
        assert notifier._url == "https://ntfy.sh/test-topic"
    
    def test_init_missing_topic(self):
        """Test that missing topic raises error."""
        with pytest.raises(ValueError, match="Topic is required"):
            NtfyNotifier(topic="")


class TestSendNotification:
    """Tests for send method."""
    
    @patch('src.notifications.ntfy.requests.post')
    def test_send_success(self, mock_post, notifier):
        """Test successful notification send."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = notifier.send("Test message")
        
        assert result is True
        mock_post.assert_called_once()
        
        # Check call arguments
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://ntfy.sh/test-topic"
        assert call_args[1]["data"] == b"Test message"
        assert call_args[1]["timeout"] == 10
    
    @patch('src.notifications.ntfy.requests.post')
    def test_send_with_title(self, mock_post, notifier):
        """Test sending notification with title."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = notifier.send("Test message", title="Test Title")
        
        assert result is True
        headers = mock_post.call_args[1]["headers"]
        assert headers["Title"] == "Test Title"
    
    @patch('src.notifications.ntfy.requests.post')
    def test_send_with_priority(self, mock_post, notifier):
        """Test sending notification with priority."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = notifier.send("Test message", priority="high")
        
        assert result is True
        headers = mock_post.call_args[1]["headers"]
        assert headers["Priority"] == "high"
    
    @patch('src.notifications.ntfy.requests.post')
    def test_send_with_tags(self, mock_post, notifier):
        """Test sending notification with tags."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = notifier.send("Test message", tags=["warning", "fire"])
        
        assert result is True
        headers = mock_post.call_args[1]["headers"]
        assert headers["Tags"] == "warning,fire"
    
    @patch('src.notifications.ntfy.requests.post')
    def test_send_timeout(self, mock_post, notifier):
        """Test that timeout raises NotificationError."""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        with pytest.raises(NotificationError, match="timeout"):
            notifier.send("Test message")
    
    @patch('src.notifications.ntfy.requests.post')
    def test_send_request_error(self, mock_post, notifier):
        """Test that request error raises NotificationError."""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")
        
        with pytest.raises(NotificationError, match="Failed to send"):
            notifier.send("Test message")
    
    @patch('src.notifications.ntfy.requests.post')
    def test_send_http_error(self, mock_post, notifier):
        """Test that HTTP error raises NotificationError."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_post.return_value = mock_response
        
        with pytest.raises(NotificationError):
            notifier.send("Test message")


class TestConvenienceMethods:
    """Tests for convenience notification methods."""
    
    @patch('src.notifications.ntfy.requests.post')
    def test_send_success_method(self, mock_post, notifier):
        """Test send_success convenience method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = notifier.send_success("Operation completed")
        
        assert result is True
        headers = mock_post.call_args[1]["headers"]
        assert headers["Title"] == "DCA Success"
        assert headers["Priority"] == "default"
        assert "white_check_mark" in headers["Tags"]
    
    @patch('src.notifications.ntfy.requests.post')
    def test_send_error_method(self, mock_post, notifier):
        """Test send_error convenience method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = notifier.send_error("Something went wrong")
        
        assert result is True
        headers = mock_post.call_args[1]["headers"]
        assert headers["Title"] == "DCA Error"
        assert headers["Priority"] == "high"
        assert "warning" in headers["Tags"]
    
    @patch('src.notifications.ntfy.requests.post')
    def test_send_info_method(self, mock_post, notifier):
        """Test send_info convenience method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = notifier.send_info("Just FYI")
        
        assert result is True
        headers = mock_post.call_args[1]["headers"]
        assert headers["Title"] == "DCA Info"
        assert headers["Priority"] == "default"
        assert "information_source" in headers["Tags"]


class TestBuildHeaders:
    """Tests for _build_headers method."""
    
    def test_build_headers_empty(self, notifier):
        """Test building headers with no parameters."""
        headers = notifier._build_headers(None, None, None)
        
        assert headers == {"Priority": "default"}
    
    def test_build_headers_with_title(self, notifier):
        """Test building headers with title."""
        headers = notifier._build_headers("Test Title", None, None)
        
        assert headers["Title"] == "Test Title"
    
    def test_build_headers_with_priority(self, notifier):
        """Test building headers with priority override."""
        headers = notifier._build_headers(None, "high", None)
        
        assert headers["Priority"] == "high"
    
    def test_build_headers_with_tags(self, notifier):
        """Test building headers with tags."""
        headers = notifier._build_headers(None, None, ["tag1", "tag2"])
        
        assert headers["Tags"] == "tag1,tag2"
    
    def test_build_headers_all_params(self, notifier):
        """Test building headers with all parameters."""
        headers = notifier._build_headers(
            "Title",
            "high",
            ["tag1", "tag2"]
        )
        
        assert headers["Title"] == "Title"
        assert headers["Priority"] == "high"
        assert headers["Tags"] == "tag1,tag2"