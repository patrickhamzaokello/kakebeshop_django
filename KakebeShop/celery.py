# KakebeShop/celery.py
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KakebeShop.settings')

app = Celery('KakebeShop')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    # Process pending notifications every minute
    'process-pending-notifications': {
        'task': 'kakebe_apps.notifications.tasks.process_pending_notifications',
        'schedule': 60.0,  # Every 60 seconds
    },

    # Retry failed notifications every 5 minutes
    'retry-failed-notifications': {
        'task': 'kakebe_apps.notifications.tasks.retry_failed_notifications',
        'schedule': 300.0,  # Every 5 minutes
    },

    # Cleanup old read notifications daily at 2 AM
    'cleanup-old-notifications': {
        'task': 'kakebe_apps.notifications.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=2, minute=0),
    },
}

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)


@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery"""
    print(f'Request: {self.request!r}')