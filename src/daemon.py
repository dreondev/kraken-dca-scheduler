"""Daemon module for scheduled DCA execution.

This module provides a long-running daemon that executes DCA trades
on a configurable schedule using APScheduler.
"""

import logging
import signal
import sys
from typing import Callable, Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import ScheduleConfig


logger = logging.getLogger(__name__)


class DCADaemon:
    """Daemon for scheduled DCA execution.
    
    Runs continuously and executes a callback function
    according to a cron schedule.
    """
    
    def __init__(
        self,
        schedule_config: ScheduleConfig,
        timezone: str,
        job_callback: Callable[[], None],
    ) -> None:
        """Initialize the DCA daemon.
        
        Args:
            schedule_config: Schedule configuration with cron expression
            timezone: Timezone for schedule (e.g., "Europe/Berlin")
            job_callback: Function to call on each scheduled execution
        """
        self._schedule_config = schedule_config
        self._timezone = timezone
        self._job_callback = job_callback
        self._scheduler: Optional[BlockingScheduler] = None
        
        logger.info("DCA Daemon initialized")
    
    def start(self) -> None:
        """Start the daemon and begin scheduled execution.
        
        This method blocks until the daemon is stopped.
        """
        if not self._schedule_config.enabled:
            logger.warning("Schedule is disabled, running single execution")
            self._job_callback()
            return
        
        self._setup_signal_handlers()
        self._scheduler = self._create_scheduler()
        self._add_job()
        
        logger.info(f"Starting daemon with schedule: {self._schedule_config.cron}")
        logger.info(f"Timezone: {self._timezone}")
        logger.info("Press Ctrl+C to stop")
        
        try:
            self._scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Daemon stopped by user")
    
    def stop(self) -> None:
        """Stop the daemon gracefully."""
        if self._scheduler and self._scheduler.running:
            logger.info("Shutting down daemon...")
            self._scheduler.shutdown(wait=False)
            logger.info("Daemon stopped")
    
    def _create_scheduler(self) -> BlockingScheduler:
        """Create and configure the APScheduler instance.
        
        Returns:
            Configured BlockingScheduler
        """
        return BlockingScheduler(
            timezone=self._timezone,
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 3600,
            },
        )
    
    def _add_job(self) -> None:
        """Add the DCA job to the scheduler."""
        trigger = self._create_trigger()
        
        self._scheduler.add_job(
            func=self._execute_job,
            trigger=trigger,
            id="dca_job",
            name="DCA Execution",
            replace_existing=True,
        )
        
        pass  # next_run_time available after scheduler.start()
    
    def _create_trigger(self) -> CronTrigger:
        """Create cron trigger from schedule config.
        
        Returns:
            Configured CronTrigger
        """
        parts = self._schedule_config.cron.split()
        
        return CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            timezone=self._timezone,
        )
    
    def _execute_job(self) -> None:
        """Execute the scheduled job with error handling."""
        logger.info("=" * 60)
        logger.info("Scheduled execution started")
        logger.info("=" * 60)
        
        try:
            self._job_callback()
            logger.info("Scheduled execution completed successfully")
        except Exception as e:
            logger.error(f"Scheduled execution failed: {e}", exc_info=True)
        
        pass  # next_run_time available after scheduler.start()
    
    def _log_next_execution(self) -> None:
        """Log the next scheduled execution time."""
        if self._scheduler:
            job = self._scheduler.get_job("dca_job")
            if job:
                next_run = job.next_run_time
                if next_run:
                    logger.info(f"Next scheduled execution: {next_run}")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _handle_signal(self, signum: int, frame) -> None:
        """Handle shutdown signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name}, initiating shutdown...")
        self.stop()
        sys.exit(0)
