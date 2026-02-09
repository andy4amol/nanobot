"""Report scheduler service for generating periodic reports.

This module provides scheduled report generation for users using APScheduler.
It supports daily, weekly, and custom report schedules.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from loguru import logger

# Try to import APScheduler
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not available. Scheduler functionality will be limited.")

from nanobot.workspace.manager import WorkspaceManager
from nanobot.services.user_config import UserConfigManager, UserConfig
from nanobot.services.report_generator_simple import ReportGenerator


class ReportScheduler:
    """
    Scheduler for periodic report generation.
    
    This class manages scheduled tasks for generating reports for users.
    It supports:
    - Daily reports at specific times
    - Weekly reports on specific days
    - Custom schedules via Cron expressions
    - One-time reports
    
    Example:
        scheduler = ReportScheduler(
            workspace_base="~/.nanobot/workspaces"
        )
        await scheduler.start()
        
        # Add daily report for user
        scheduler.add_daily_report_job(
            user_id="user_123",
            hour=9,
            minute=0
        )
    """
    
    def __init__(
        self,
        workspace_base: str = "~/.nanobot/workspaces",
        report_generator: Optional[Any] = None
    ):
        """
        Initialize the ReportScheduler.
        
        Args:
            workspace_base: Base path for user workspaces
            report_generator: Optional report generator instance
        """
        self.workspace_base = Path(workspace_base).expanduser()
        self.workspace_manager = WorkspaceManager(workspace_base)
        self.config_manager = UserConfigManager(workspace_base)
        self.report_generator = report_generator
        
        # Storage for job information
        self.jobs: Dict[str, Any] = {}
        
        # Initialize scheduler if available
        if APSCHEDULER_AVAILABLE:
            self.scheduler = AsyncIOScheduler(
                jobstores={
                    'default': MemoryJobStore()
                },
                job_defaults={
                    'coalesce': False,
                    'max_instances': 3
                }
            )
        else:
            self.scheduler = None
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self.scheduler:
            self.scheduler.start()
            logger.info("ReportScheduler started")
        else:
            logger.warning("Scheduler not available (APScheduler not installed)")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("ReportScheduler stopped")
    
    def add_daily_report_job(
        self,
        user_id: str,
        hour: int = 9,
        minute: int = 0,
        report_type: str = "daily"
    ) -> Optional[str]:
        """
        Add a daily report job for a user.
        
        Args:
            user_id: User identifier
            hour: Hour of day (0-23)
            minute: Minute of hour (0-59)
            report_type: Type of report
            
        Returns:
            Job ID if successful, None otherwise
        """
        if not self.scheduler:
            logger.warning("Cannot add job: scheduler not available")
            return None
        
        job_id = f"daily_report_{user_id}"
        
        # Remove existing job if any
        if job_id in self.jobs:
            try:
                self.scheduler.remove_job(job_id)
            except Exception as e:
                logger.warning(f"Failed to remove existing job {job_id}: {e}")
        
        # Create trigger for daily execution
        trigger = CronTrigger(hour=hour, minute=minute)
        
        # Add job
        try:
            job = self.scheduler.add_job(
                func=self._generate_report_task,
                trigger=trigger,
                id=job_id,
                args=[user_id, report_type],
                replace_existing=True
            )
            
            self.jobs[job_id] = {
                "user_id": user_id,
                "type": "daily",
                "schedule": f"{hour:02d}:{minute:02d}",
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            }
            
            logger.info(f"Added daily report job for {user_id} at {hour:02d}:{minute:02d}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to add job: {e}")
            return None
    
    def add_weekly_report_job(
        self,
        user_id: str,
        day_of_week: str = "mon",
        hour: int = 9,
        minute: int = 0,
        report_type: str = "weekly"
    ) -> Optional[str]:
        """
        Add a weekly report job for a user.
        
        Args:
            user_id: User identifier
            day_of_week: Day of week (mon, tue, wed, thu, fri, sat, sun)
            hour: Hour of day (0-23)
            minute: Minute of hour (0-59)
            report_type: Type of report
            
        Returns:
            Job ID if successful, None otherwise
        """
        if not self.scheduler:
            logger.warning("Cannot add job: scheduler not available")
            return None
        
        job_id = f"weekly_report_{user_id}"
        
        # Map day names to numbers
        day_map = {
            "mon": 0, "tue": 1, "wed": 2, "thu": 3,
            "fri": 4, "sat": 5, "sun": 6
        }
        day_num = day_map.get(day_of_week.lower(), 0)
        
        # Remove existing job if any
        if job_id in self.jobs:
            try:
                self.scheduler.remove_job(job_id)
            except Exception as e:
                logger.warning(f"Failed to remove existing job {job_id}: {e}")
        
        # Create trigger for weekly execution
        trigger = CronTrigger(day_of_week=day_num, hour=hour, minute=minute)
        
        # Add job
        try:
            job = self.scheduler.add_job(
                func=self._generate_report_task,
                trigger=trigger,
                id=job_id,
                args=[user_id, report_type],
                replace_existing=True
            )
            
            self.jobs[job_id] = {
                "user_id": user_id,
                "type": "weekly",
                "schedule": f"{day_of_week} {hour:02d}:{minute:02d}",
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            }
            
            logger.info(f"Added weekly report job for {user_id} on {day_of_week} at {hour:02d}:{minute:02d}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to add job: {e}")
            return None
    
    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job.
        
        Args:
            job_id: The job ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        if not self.scheduler:
            return False
        
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.jobs:
                del self.jobs[job_id]
            logger.info(f"Removed job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")
            return False
    
    def get_user_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all scheduled jobs for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of job information dictionaries
        """
        user_jobs = []
        for job_id, job_info in self.jobs.items():
            if job_info.get("user_id") == user_id:
                user_jobs.append({
                    "job_id": job_id,
                    **job_info
                })
        return user_jobs
    
    def get_all_jobs(self) -> Dict[str, Any]:
        """
        Get all scheduled jobs.
        
        Returns:
            Dictionary with job information
        """
        return {
            "total_jobs": len(self.jobs),
            "jobs": self.jobs
        }
    
    async def _generate_report_task(self, user_id: str, report_type: str) -> None:
        """
        Background task for generating a report.
        
        This is called by the scheduler when a job is triggered.
        
        Args:
            user_id: User identifier
            report_type: Type of report to generate
        """
        logger.info(f"Starting report generation for {user_id}: {report_type}")
        
        try:
            # Get user config
            config = self.config_manager.get_config(user_id)
            if not config:
                logger.error(f"User {user_id} not found for report generation")
                return
            
            # Use report generator if available
            if self.report_generator:
                result = await self.report_generator.generate_report(
                    user_id=user_id,
                    report_type=report_type
                )
                logger.info(f"Report generated for {user_id}: {result}")
            else:
                # Placeholder for when report_generator is not available
                logger.info(f"Report generation for {user_id} would happen here")
                
                # Create a placeholder report file
                reports_dir = self.workspace_manager.get_workspace(user_id) / "reports"
                reports_dir.mkdir(exist_ok=True)
                
                report_id = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                report_file = reports_dir / f"{report_id}.md"
                
                report_content = f"""# {report_type.capitalize()} Report

**User:** {user_id}  
**Generated:** {datetime.now().isoformat()}  
**Type:** {report_type}

## Summary

This is a placeholder report. The actual report content would be generated by the AI assistant based on the user's watchlist and preferences.

## Watchlist Summary

- **Stocks:** {', '.join(config.watchlist.stocks) if config.watchlist.stocks else 'None'}
- **Influencers:** {', '.join(config.watchlist.influencers) if config.watchlist.influencers else 'None'}
- **Keywords:** {', '.join(config.watchlist.keywords) if config.watchlist.keywords else 'None'}

---

*This report was automatically generated by nanobot.*
"""
                
                report_file.write_text(report_content, encoding="utf-8")
                logger.info(f"Placeholder report saved to {report_file}")
        
        except Exception as e:
            logger.error(f"Failed to generate report for {user_id}: {e}")
    
    async def generate_report_now(
        self,
        user_id: str,
        report_type: str = "custom"
    ) -> Optional[str]:
        """
        Generate a report immediately (not scheduled).
        
        Args:
            user_id: User identifier
            report_type: Type of report
            
        Returns:
            Report ID if successful, None otherwise
        """
        logger.info(f"Manually triggering report generation for {user_id}")
        
        try:
            await self._generate_report_task(user_id, report_type)
            return f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        except Exception as e:
            logger.error(f"Manual report generation failed for {user_id}: {e}")
            return None
