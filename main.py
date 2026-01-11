"""Kraken DCA Scheduler - Entry Point.

This is the main entry point for the DCA scheduler application.
It loads configuration, initializes components, and executes the DCA strategy.
"""

import sys
from pathlib import Path

from src.config import Config
from src.kraken.client import KrakenClient
from src.logger import setup_logger
from src.notifications.ntfy import NtfyNotifier
from src.scheduler import DCAScheduler


def main() -> int:
    """Main entry point for DCA scheduler.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Load configuration
    try:
        config = Config.load()
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return 1
    
    # Setup logging
    logger = setup_logger(
        name="kraken-dca",
        level=config.general.log_level,
        log_file="script.log",
    )
    
    logger.info("=" * 70)
    logger.info("Kraken DCA Scheduler - Starting")
    logger.info("=" * 70)
    
    try:
        # Initialize Kraken client
        kraken_client = KrakenClient(
            api_key=config.kraken.api_key,
            api_secret=config.kraken.api_secret,
        )
        
        # Initialize notifier (optional)
        notifier = None
        if config.notifications and config.notifications.enabled:
            if config.notifications.provider == "ntfy" and config.notifications.ntfy:
                notifier = NtfyNotifier(
                    server=config.notifications.ntfy.server,
                    topic=config.notifications.ntfy.topic,
                    priority=config.notifications.ntfy.priority,
                )
                logger.info("ntfy notifier initialized")
            else:
                logger.warning("Notification provider configured but not supported")
        elif config.telegram:
            # Legacy Telegram support (fallback)
            logger.info("Using legacy Telegram configuration")
            logger.warning("Consider migrating to ntfy.sh - see config.example.yaml")
            # Note: We're not implementing Telegram here anymore
            # Users should migrate to ntfy
        
        # Initialize and execute DCA scheduler
        scheduler = DCAScheduler(
            config=config,
            kraken_client=kraken_client,
            notifier=notifier,
        )
        
        result = scheduler.execute()
        
        if result.success:
            logger.info("DCA execution completed successfully")
            return 0
        else:
            logger.error("DCA execution failed")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Execution interrupted by user")
        return 130
        
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        return 1
    
    finally:
        logger.info("=" * 70)
        logger.info("Kraken DCA Scheduler - Finished")
        logger.info("=" * 70)


if __name__ == "__main__":
    sys.exit(main())