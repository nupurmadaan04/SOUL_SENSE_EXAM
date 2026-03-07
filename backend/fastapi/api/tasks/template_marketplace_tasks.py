"""
Template Marketplace Celery Tasks

Background tasks for template processing, analytics aggregation,
export job processing, and marketplace maintenance.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

try:
    from celery import Celery, chain, group
    from celery.exceptions import MaxRetriesExceededError
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    class MockCelery:
        def task(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    Celery = MockCelery

from backend.fastapi.api.utils.template_marketplace import (
    get_marketplace_manager,
    TemplateFormat,
    TemplateStatus,
    reset_marketplace_manager
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery('template_marketplace')


# Task 1: Process Pending Export Jobs
@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_pending_export_jobs(self):
    """
    Process pending template export jobs.
    
    Runs: Every 5 minutes
    """
    try:
        logger.info("Starting pending export jobs processing")
        
        async def _process():
            manager = await get_marketplace_manager()
            processed = 0
            failed = 0
            
            pending_jobs = [
                job for job in manager.export_jobs.values()
                if job.status == "pending"
            ]
            
            for job in pending_jobs[:10]:  # Process up to 10 at a time
                try:
                    # Update status to processing
                    await manager.update_export_job_status(
                        job.job_id,
                        "processing"
                    )
                    
                    # Simulate export processing
                    # In production, this would:
                    # 1. Get template content
                    # 2. Populate with data
                    # 3. Generate output in requested format
                    # 4. Upload to storage
                    # 5. Update job with output URL
                    
                    # Mock processing
                    import time
                    start_time = time.time()
                    
                    # Generate mock output URL
                    output_url = f"https://storage.example.com/exports/{job.job_id}.{job.output_format.value}"
                    file_size = len(str(job.data)) * 10  # Mock size
                    checksum = f"checksum_{job.job_id}"
                    
                    processing_time = int((time.time() - start_time) * 1000)
                    
                    await manager.update_export_job_status(
                        job.job_id,
                        "completed",
                        output_url=output_url,
                        file_size_bytes=file_size,
                        checksum=checksum,
                        processing_time_ms=processing_time
                    )
                    
                    processed += 1
                    logger.info(f"Completed export job: {job.job_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to process export job {job.job_id}: {e}")
                    await manager.update_export_job_status(
                        job.job_id,
                        "failed",
                        error_message=str(e)
                    )
                    failed += 1
            
            return {
                "processed": processed,
                "failed": failed,
                "remaining": len([j for j in manager.export_jobs.values() if j.status == "pending"])
            }
        
        result = asyncio.run(_process())
        logger.info(f"Export jobs processing completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error processing export jobs: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for process_pending_export_jobs")
            return {"error": str(exc)}


# Task 2: Cleanup Old Export Jobs
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def cleanup_old_export_jobs(self, days_old: int = 7):
    """
    Clean up old completed/failed export jobs.
    
    Runs: Daily
    """
    try:
        logger.info(f"Starting cleanup of export jobs older than {days_old} days")
        
        async def _cleanup():
            manager = await get_marketplace_manager()
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            removed = 0
            
            job_ids_to_remove = []
            for job_id, job in manager.export_jobs.items():
                if job.status in ["completed", "failed"]:
                    if job.completed_at and job.completed_at < cutoff_date:
                        job_ids_to_remove.append(job_id)
            
            for job_id in job_ids_to_remove:
                del manager.export_jobs[job_id]
                removed += 1
            
            return {
                "removed": removed,
                "remaining": len(manager.export_jobs)
            }
        
        result = asyncio.run(_cleanup())
        logger.info(f"Export jobs cleanup completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error cleaning up export jobs: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for cleanup_old_export_jobs")
            return {"error": str(exc)}


# Task 3: Generate Daily Analytics Report
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def generate_daily_analytics_report(self):
    """
    Generate daily marketplace analytics report.
    
    Runs: Daily at midnight
    """
    try:
        logger.info("Starting daily analytics report generation")
        
        async def _generate():
            manager = await get_marketplace_manager()
            
            # Get yesterday's date
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)
            
            # Get analytics for the period
            events = await manager.get_analytics(
                start_time=start_time,
                end_time=end_time,
                limit=10000
            )
            
            # Aggregate metrics
            views = len([e for e in events if e.event_type == "view"])
            downloads = len([e for e in events if e.event_type == "download"])
            purchases = len([e for e in events if e.event_type == "purchase"])
            
            # Top templates
            template_events = defaultdict(lambda: {"views": 0, "downloads": 0})
            for event in events:
                if event.event_type == "view":
                    template_events[event.template_id]["views"] += 1
                elif event.event_type == "download":
                    template_events[event.template_id]["downloads"] += 1
            
            top_templates = sorted(
                template_events.items(),
                key=lambda x: x[1]["downloads"],
                reverse=True
            )[:10]
            
            report = {
                "date": start_time.strftime("%Y-%m-%d"),
                "generated_at": datetime.utcnow().isoformat(),
                "metrics": {
                    "total_events": len(events),
                    "views": views,
                    "downloads": downloads,
                    "purchases": purchases
                },
                "top_templates": [
                    {
                        "template_id": tid,
                        "views": data["views"],
                        "downloads": data["downloads"]
                    }
                    for tid, data in top_templates
                ]
            }
            
            logger.info(f"Daily analytics report generated: {len(events)} events")
            return report
        
        result = asyncio.run(_generate())
        return result
        
    except Exception as exc:
        logger.error(f"Error generating analytics report: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for generate_daily_analytics_report")
            return {"error": str(exc)}


# Task 4: Update Template Popularity Scores
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def update_template_popularity_scores(self):
    """
    Update template popularity scores based on engagement.
    
    Runs: Hourly
    """
    try:
        logger.info("Starting popularity score updates")
        
        async def _update():
            manager = await get_marketplace_manager()
            
            updated = 0
            
            for template in manager.templates.values():
                # Calculate popularity score
                # Formula: (downloads * 3) + (views * 0.1) + (rating * reviews * 2)
                score = (
                    template.download_count * 3 +
                    template.view_count * 0.1 +
                    template.average_rating * template.total_reviews * 2
                )
                
                # Update metadata
                template.metadata["popularity_score"] = round(score, 2)
                
                # Auto-feature popular templates
                if score > 100 and template.status == TemplateStatus.PUBLISHED:
                    if not template.is_featured:
                        template.is_featured = True
                        logger.info(f"Auto-featured template: {template.template_id}")
                
                updated += 1
            
            return {"updated": updated}
        
        result = asyncio.run(_update())
        logger.info(f"Popularity scores updated: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error updating popularity scores: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for update_template_popularity_scores")
            return {"error": str(exc)}


# Task 5: Send Expiring Subscription Reminders
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def send_expiring_subscription_reminders(self, days_before: int = 7):
    """
    Send reminders for expiring template subscriptions.
    
    Runs: Daily
    """
    try:
        logger.info(f"Starting expiring subscription reminders ({days_before} days)")
        
        async def _send():
            manager = await get_marketplace_manager()
            
            reminder_date = datetime.utcnow() + timedelta(days=days_before)
            notified = 0
            
            for user_id, library in manager.user_libraries.items():
                for entry in library:
                    if entry.expires_at:
                        # Check if expires within the window
                        days_until_expiry = (entry.expires_at - datetime.utcnow()).days
                        
                        if days_until_expiry == days_before:
                            # In production, send email/notification
                            logger.info(
                                f"Would send reminder to user {user_id} "
                                f"for template {entry.template_id}"
                            )
                            notified += 1
            
            return {"notifications_sent": notified}
        
        result = asyncio.run(_send())
        logger.info(f"Expiring subscription reminders completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error sending reminders: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for send_expiring_subscription_reminders")
            return {"error": str(exc)}


# Task 6: Archive Old Template Versions
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def archive_old_template_versions(self, versions_to_keep: int = 5):
    """
    Archive old template versions, keeping only the most recent ones.
    
    Runs: Weekly
    """
    try:
        logger.info(f"Starting old version archival (keeping {versions_to_keep})")
        
        async def _archive():
            manager = await get_marketplace_manager()
            
            archived = 0
            
            for template in manager.templates.values():
                if len(template.versions) > versions_to_keep:
                    # Sort by created date
                    sorted_versions = sorted(
                        template.versions,
                        key=lambda v: v.created_at,
                        reverse=True
                    )
                    
                    # Keep current version and recent ones
                    versions_to_archive = sorted_versions[versions_to_keep:]
                    
                    for version in versions_to_archive:
                        if not version.is_current:
                            version.status = TemplateStatus.ARCHIVED
                            archived += 1
            
            return {"archived": archived}
        
        result = asyncio.run(_archive())
        logger.info(f"Old version archival completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error archiving old versions: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for archive_old_template_versions")
            return {"error": str(exc)}


# Task 7: Moderate Pending Reviews
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def moderate_pending_reviews(self):
    """
    Moderate pending template reviews.
    
    Runs: Every 6 hours
    """
    try:
        logger.info("Starting review moderation")
        
        async def _moderate():
            manager = await get_marketplace_manager()
            
            from backend.fastapi.api.utils.template_marketplace import ReviewStatus
            
            approved = 0
            rejected = 0
            
            for template in manager.templates.values():
                for review in template.reviews:
                    if review.status == ReviewStatus.PENDING:
                        # Simple moderation logic
                        # In production, use ML or manual review
                        
                        # Auto-approve if rating is 3-5 and no spam indicators
                        if 3 <= review.rating <= 5:
                            # Check for spam (very long comments, repeated text, etc.)
                            if review.comment:
                                if len(review.comment) < 1000 and not _is_spam(review.comment):
                                    review.status = ReviewStatus.APPROVED
                                    approved += 1
                                else:
                                    review.status = ReviewStatus.FLAGGED
                            else:
                                review.status = ReviewStatus.APPROVED
                                approved += 1
                        else:
                            # Flag low ratings for manual review
                            review.status = ReviewStatus.FLAGGED
                            rejected += 1
            
            return {"approved": approved, "rejected": rejected}
        
        def _is_spam(text: str) -> bool:
            """Simple spam detection."""
            # Check for repeated characters
            if re.search(r'(.)\1{10,}', text):
                return True
            # Check for excessive URLs
            if text.count('http') > 3:
                return True
            return False
        
        result = asyncio.run(_moderate())
        logger.info(f"Review moderation completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error moderating reviews: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for moderate_pending_reviews")
            return {"error": str(exc)}


# Task 8: Generate Weekly Marketplace Digest
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def generate_weekly_digest(self):
    """
    Generate weekly marketplace digest for administrators.
    
    Runs: Weekly on Mondays
    """
    try:
        logger.info("Starting weekly digest generation")
        
        async def _generate():
            manager = await get_marketplace_manager()
            
            # Get statistics
            stats = await manager.get_statistics()
            
            # Get top performing templates
            top_templates = sorted(
                manager.templates.values(),
                key=lambda t: t.download_count,
                reverse=True
            )[:5]
            
            # Get newest templates
            new_templates = sorted(
                [t for t in manager.templates.values() if t.status == TemplateStatus.PUBLISHED],
                key=lambda t: t.created_at,
                reverse=True
            )[:5]
            
            digest = {
                "period": "weekly",
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "total_templates": stats["templates"]["total"],
                    "total_downloads": stats["engagement"]["total_downloads"],
                    "total_views": stats["engagement"]["total_views"],
                    "average_rating": stats["engagement"]["average_rating"]
                },
                "top_performers": [
                    {
                        "template_id": t.template_id,
                        "name": t.name,
                        "downloads": t.download_count,
                        "rating": t.average_rating
                    }
                    for t in top_templates
                ],
                "new_templates": [
                    {
                        "template_id": t.template_id,
                        "name": t.name,
                        "category": t.category.value,
                        "created_at": t.created_at.isoformat()
                    }
                    for t in new_templates
                ],
                "jobs_summary": stats["jobs"]
            }
            
            logger.info("Weekly digest generated successfully")
            return digest
        
        result = asyncio.run(_generate())
        return result
        
    except Exception as exc:
        logger.error(f"Error generating weekly digest: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for generate_weekly_digest")
            return {"error": str(exc)}


# Task 9: Sync Template Index
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def sync_template_index(self):
    """
    Sync template search index.
    
    Runs: Hourly
    """
    try:
        logger.info("Starting template index sync")
        
        async def _sync():
            manager = await get_marketplace_manager()
            
            # Build search index
            index = []
            for template in manager.templates.values():
                if template.status == TemplateStatus.PUBLISHED:
                    index.append({
                        "template_id": template.template_id,
                        "name": template.name,
                        "description": template.description,
                        "category": template.category.value,
                        "tags": template.tags,
                        "average_rating": template.average_rating,
                        "download_count": template.download_count
                    })
            
            # In production, send to search service (Elasticsearch, Algolia, etc.)
            logger.info(f"Synced {len(index)} templates to search index")
            
            return {"indexed": len(index)}
        
        result = asyncio.run(_sync())
        return result
        
    except Exception as exc:
        logger.error(f"Error syncing template index: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for sync_template_index")
            return {"error": str(exc)}


# Task 10: Cleanup Unused Library Entries
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def cleanup_unused_library_entries(self, unused_days: int = 365):
    """
    Clean up library entries that haven't been used in a long time.
    
    Runs: Monthly
    """
    try:
        logger.info(f"Starting cleanup of unused library entries ({unused_days} days)")
        
        async def _cleanup():
            manager = await get_marketplace_manager()
            
            cutoff_date = datetime.utcnow() - timedelta(days=unused_days)
            removed = 0
            
            for user_id, library in list(manager.user_libraries.items()):
                entries_to_remove = [
                    entry for entry in library
                    if entry.last_used_at and entry.last_used_at < cutoff_date
                ]
                
                for entry in entries_to_remove:
                    library.remove(entry)
                    removed += 1
            
            return {"removed": removed}
        
        result = asyncio.run(_cleanup())
        logger.info(f"Unused library entries cleanup completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error cleaning up library entries: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for cleanup_unused_library_entries")
            return {"error": str(exc)}


# Celery Beat Schedule Configuration
"""
Add to Celery configuration:

CELERY_BEAT_SCHEDULE = {
    'process-pending-exports': {
        'task': 'api.tasks.template_marketplace_tasks.process_pending_export_jobs',
        'schedule': 300.0,  # Every 5 minutes
    },
    'cleanup-old-exports': {
        'task': 'api.tasks.template_marketplace_tasks.cleanup_old_export_jobs',
        'schedule': 86400.0,  # Daily
    },
    'daily-analytics': {
        'task': 'api.tasks.template_marketplace_tasks.generate_daily_analytics_report',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
    'update-popularity': {
        'task': 'api.tasks.template_marketplace_tasks.update_template_popularity_scores',
        'schedule': 3600.0,  # Hourly
    },
    'subscription-reminders': {
        'task': 'api.tasks.template_marketplace_tasks.send_expiring_subscription_reminders',
        'schedule': 86400.0,  # Daily
    },
    'archive-old-versions': {
        'task': 'api.tasks.template_marketplace_tasks.archive_old_template_versions',
        'schedule': 604800.0,  # Weekly
    },
    'moderate-reviews': {
        'task': 'api.tasks.template_marketplace_tasks.moderate_pending_reviews',
        'schedule': 21600.0,  # Every 6 hours
    },
    'weekly-digest': {
        'task': 'api.tasks.template_marketplace_tasks.generate_weekly_digest',
        'schedule': crontab(day_of_week=1, hour=9, minute=0),  # Mondays at 9 AM
    },
    'sync-search-index': {
        'task': 'api.tasks.template_marketplace_tasks.sync_template_index',
        'schedule': 3600.0,  # Hourly
    },
    'cleanup-library': {
        'task': 'api.tasks.template_marketplace_tasks.cleanup_unused_library_entries',
        'schedule': 2592000.0,  # Monthly
    },
}
"""
