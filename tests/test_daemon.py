"""Tests for daemon module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.config import ScheduleConfig
from src.daemon import DCADaemon


class TestDCADaemonInit:
    """Tests for DCADaemon initialization."""
    
    def test_init_with_valid_config(self):
        """Test daemon initialization with valid config."""
        config = ScheduleConfig(enabled=True, cron="0 8 * * *")
        callback = Mock()
        
        daemon = DCADaemon(
            schedule_config=config,
            timezone="Europe/Berlin",
            job_callback=callback,
        )
        
        assert daemon._schedule_config == config
        assert daemon._timezone == "Europe/Berlin"
        assert daemon._job_callback == callback
        assert daemon._scheduler is None
    
    def test_init_with_disabled_schedule(self):
        """Test daemon initialization with disabled schedule."""
        config = ScheduleConfig(enabled=False, cron="")
        callback = Mock()
        
        daemon = DCADaemon(
            schedule_config=config,
            timezone="Europe/Berlin",
            job_callback=callback,
        )
        
        assert daemon._schedule_config.enabled is False


class TestDCADaemonStart:
    """Tests for DCADaemon.start() method."""
    
    def test_start_with_disabled_schedule_runs_once(self):
        """Test that disabled schedule runs callback once."""
        config = ScheduleConfig(enabled=False, cron="")
        callback = Mock()
        
        daemon = DCADaemon(
            schedule_config=config,
            timezone="Europe/Berlin",
            job_callback=callback,
        )
        
        daemon.start()
        
        callback.assert_called_once()
    
    @patch("src.daemon.BlockingScheduler")
    def test_start_with_enabled_schedule_creates_scheduler(self, mock_scheduler_class):
        """Test that enabled schedule creates scheduler."""
        config = ScheduleConfig(enabled=True, cron="0 8 * * *")
        callback = Mock()
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_job = MagicMock()
        mock_job.next_run_time = "2026-01-28 08:00:00"
        mock_scheduler.get_job.return_value = mock_job
        
        daemon = DCADaemon(
            schedule_config=config,
            timezone="Europe/Berlin",
            job_callback=callback,
        )
        
        daemon.start()
        
        mock_scheduler_class.assert_called_once()
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()


class TestDCADaemonStop:
    """Tests for DCADaemon.stop() method."""
    
    def test_stop_without_scheduler(self):
        """Test stop when scheduler is not initialized."""
        config = ScheduleConfig(enabled=False, cron="")
        callback = Mock()
        
        daemon = DCADaemon(
            schedule_config=config,
            timezone="Europe/Berlin",
            job_callback=callback,
        )
        
        daemon.stop()
    
    def test_stop_with_running_scheduler(self):
        """Test stop when scheduler is running."""
        config = ScheduleConfig(enabled=True, cron="0 8 * * *")
        callback = Mock()
        
        daemon = DCADaemon(
            schedule_config=config,
            timezone="Europe/Berlin",
            job_callback=callback,
        )
        
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        daemon._scheduler = mock_scheduler
        
        daemon.stop()
        
        mock_scheduler.shutdown.assert_called_once_with(wait=False)


class TestDCADaemonCreateTrigger:
    """Tests for DCADaemon._create_trigger() method."""
    
    def test_create_trigger_returns_cron_trigger(self):
        """Test that _create_trigger returns a CronTrigger."""
        from apscheduler.triggers.cron import CronTrigger
        
        config = ScheduleConfig(enabled=True, cron="0 8 * * *")
        callback = Mock()
        
        daemon = DCADaemon(
            schedule_config=config,
            timezone="Europe/Berlin",
            job_callback=callback,
        )
        
        trigger = daemon._create_trigger()
        
        assert isinstance(trigger, CronTrigger)
    
    def test_create_trigger_uses_correct_timezone(self):
        """Test that trigger uses configured timezone."""
        config = ScheduleConfig(enabled=True, cron="0 8 * * *")
        callback = Mock()
        
        daemon = DCADaemon(
            schedule_config=config,
            timezone="Europe/Berlin",
            job_callback=callback,
        )
        
        trigger = daemon._create_trigger()
        
        assert str(trigger.timezone) == "Europe/Berlin"


class TestDCADaemonExecuteJob:
    """Tests for DCADaemon._execute_job() method."""
    
    def test_execute_job_success(self):
        """Test successful job execution."""
        config = ScheduleConfig(enabled=True, cron="0 8 * * *")
        callback = Mock()
        
        daemon = DCADaemon(
            schedule_config=config,
            timezone="Europe/Berlin",
            job_callback=callback,
        )
        
        daemon._execute_job()
        
        callback.assert_called_once()
    
    def test_execute_job_handles_exception(self):
        """Test that job execution handles exceptions."""
        config = ScheduleConfig(enabled=True, cron="0 8 * * *")
        callback = Mock(side_effect=Exception("Test error"))
        
        daemon = DCADaemon(
            schedule_config=config,
            timezone="Europe/Berlin",
            job_callback=callback,
        )
        
        daemon._execute_job()
        
        callback.assert_called_once()
