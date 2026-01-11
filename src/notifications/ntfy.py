"""ntfy.sh notification client for Kraken DCA Scheduler.

This module provides a simple interface to send notifications
via ntfy.sh, replacing the more complex Telegram bot setup.
"""

import logging
from typing import Optional

import requests


logger = logging.getLogger(__name__)


class NotificationError(Exception):
    """Base exception for notification errors."""
    pass


class NtfyNotifier:
    """Simple ntfy.sh notification client.
    
    ntfy.sh is a simple pub-sub notification service that doesn't
    require authentication or bot tokens. Much simpler than Telegram!
    """
    
    def __init__(
        self,
        server: str = "https://ntfy.sh",
        topic: str = "",
        priority: str = "default",
        timeout: int = 10,
    ):
        """Initialize ntfy notifier.
        
        Args:
            server: ntfy server URL (default: https://ntfy.sh)
            topic: Topic name (must be unique!)
            priority: Message priority (min, low, default, high, max)
            timeout: Request timeout in seconds
            
        Raises:
            ValueError: If topic is empty
        """
        if not topic:
            raise ValueError("Topic is required for ntfy notifications")
        
        self._server = server.rstrip("/")
        self._topic = topic
        self._priority = priority
        self._timeout = timeout
        self._url = f"{self._server}/{self._topic}"
        
        logger.info(f"ntfy notifier initialized for topic: {self._topic}")
    
    def send(
        self,
        message: str,
        title: Optional[str] = None,
        priority: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> bool:
        """Send notification to ntfy topic.
        
        Args:
            message: Notification message body
            title: Optional message title
            priority: Optional priority override (min, low, default, high, max)
            tags: Optional list of emoji tags (e.g., ["warning", "chart"])
        
        Returns:
            True if notification sent successfully
            
        Raises:
            NotificationError: If notification fails
            
        Examples:
            >>> notifier = NtfyNotifier(topic="my-topic")
            >>> notifier.send("Trade executed", title="DCA Bot")
            True
            
            >>> notifier.send(
            ...     "Order placed",
            ...     priority="high",
            ...     tags=["money_with_wings"]
            ... )
            True
        """
        logger.info(f"Sending notification: {title or 'No title'}")
        
        headers = self._build_headers(title, priority, tags)
        
        try:
            response = requests.post(
                self._url,
                data=message.encode("utf-8"),
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            
            logger.info("Notification sent successfully")
            return True
            
        except requests.exceptions.Timeout:
            error_msg = f"Notification timeout after {self._timeout}s"
            logger.error(error_msg)
            raise NotificationError(error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to send notification: {e}"
            logger.error(error_msg)
            raise NotificationError(error_msg)
    
    def send_success(self, message: str, title: str = "DCA Success") -> bool:
        """Send success notification with green theme.
        
        Args:
            message: Success message
            title: Title (default: "DCA Success")
        
        Returns:
            True if sent successfully
        """
        return self.send(
            message=message,
            title=title,
            priority="default",
            tags=["white_check_mark"],
        )
    
    def send_error(self, message: str, title: str = "DCA Error") -> bool:
        """Send error notification with high priority.
        
        Args:
            message: Error message
            title: Title (default: "DCA Error")
        
        Returns:
            True if sent successfully
        """
        return self.send(
            message=message,
            title=title,
            priority="high",
            tags=["x", "warning"],
        )
    
    def send_info(self, message: str, title: str = "DCA Info") -> bool:
        """Send info notification.
        
        Args:
            message: Info message
            title: Title (default: "DCA Info")
        
        Returns:
            True if sent successfully
        """
        return self.send(
            message=message,
            title=title,
            priority="default",
            tags=["information_source"],
        )
    
    def _build_headers(
        self,
        title: Optional[str],
        priority: Optional[str],
        tags: Optional[list[str]],
    ) -> dict[str, str]:
        """Build request headers for ntfy.
        
        Args:
            title: Message title
            priority: Message priority
            tags: Message tags
        
        Returns:
            Dictionary of HTTP headers
        """
        headers = {}
        
        if title:
            headers["Title"] = title
        
        if priority:
            headers["Priority"] = priority
        elif self._priority:
            headers["Priority"] = self._priority
        
        if tags:
            headers["Tags"] = ",".join(tags)
        
        return headers