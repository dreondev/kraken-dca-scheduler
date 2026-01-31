"""Kraken DCA Scheduler - Entry Point.

This is the main entry point for the DCA scheduler application.
It loads configuration, initializes components, and executes the DCA strategy.

Supports two modes:
- Single execution: Runs once and exits (schedule.enabled: false)
- Daemon mode: Runs continuously on schedule (schedule.enabled: true)
"""

import logging
import sys

from src.config import Config
from src.daemon import DCADaemon
from src.kraken.client import KrakenClient
from src.logger import setup_logger
from src.notifications.ntfy import NtfyNotifier
from src.scheduler import DCAScheduler


def main() -> int:
    """Main entry point for DCA scheduler.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        config = Config.load()
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return 1
    
    logger = setup_logger(
        name="src",
        level=config.general.log_level,
        log_file="script.log",
    )
    
    logger.info("=" * 70)
    logger.info("Kraken DCA Scheduler - Starting")
    logger.info("=" * 70)
    
    try:
        kraken_client = _create_kraken_client(config)
        notifier = _create_notifier(config, logger)
        dca_scheduler = _create_dca_scheduler(config, kraken_client, notifier)
        
        if _is_daemon_mode(config):
            return _run_daemon(config, dca_scheduler, logger)
        else:
            return _run_single_execution(dca_scheduler, logger)
            
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


def _create_kraken_client(config: Config) -> KrakenClient:
    """Create and return Kraken API client.
    
    Args:
        config: Application configuration
    
    Returns:
        Configured KrakenClient
    """
    return KrakenClient(
        api_key=config.kraken.api_key,
        api_secret=config.kraken.api_secret,
    )


def _create_notifier(config: Config, logger) -> NtfyNotifier | None:
    """Create and return notification client if configured.
    
    Args:
        config: Application configuration
        logger: Logger instance
    
    Returns:
        Configured NtfyNotifier or None
    """
    if not config.notifications or not config.notifications.enabled:
        return None
    
    if config.notifications.provider == "ntfy" and config.notifications.ntfy:
        notifier = NtfyNotifier(
            server=config.notifications.ntfy.server,
            topic=config.notifications.ntfy.topic,
            priority=config.notifications.ntfy.priority,
        )
        logger.info("ntfy notifier initialized")
        return notifier
    
    logger.warning("Notification provider configured but not supported")
    return None


def _create_dca_scheduler(
    config: Config,
    kraken_client: KrakenClient,
    notifier: NtfyNotifier | None,
) -> DCAScheduler:
    """Create and return DCA scheduler.
    
    Args:
        config: Application configuration
        kraken_client: Kraken API client
        notifier: Optional notification client
    
    Returns:
        Configured DCAScheduler
    """
    return DCAScheduler(
        config=config,
        kraken_client=kraken_client,
        notifier=notifier,
    )


def _is_daemon_mode(config: Config) -> bool:
    """Check if daemon mode is enabled.
    
    Args:
        config: Application configuration
    
    Returns:
        True if daemon mode is enabled
    """
    return config.schedule is not None and config.schedule.enabled


def _run_daemon(config: Config, dca_scheduler: DCAScheduler, logger) -> int:
    """Run in daemon mode with scheduled execution.
    
    Args:
        config: Application configuration
        dca_scheduler: DCA scheduler instance
        logger: Logger instance
    
    Returns:
        Exit code (0 for success)
    """
    logger.info("Starting in daemon mode")
    logger.info(f"Schedule: {config.schedule.cron}")
    logger.info(f"Timezone: {config.general.timezone}")
    
    daemon = DCADaemon(
        schedule_config=config.schedule,
        timezone=config.general.timezone,
        job_callback=dca_scheduler.execute,
    )
    
    daemon.start()
    return 0


def _run_single_execution(dca_scheduler: DCAScheduler, logger) -> int:
    """Run single DCA execution.
    
    Args:
        dca_scheduler: DCA scheduler instance
        logger: Logger instance
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("Running single execution")
    
    result = dca_scheduler.execute()
    
    if result.success:
        logger.info("DCA execution completed successfully")
        return 0
    else:
        logger.error("DCA execution failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())