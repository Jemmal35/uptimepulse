import os
from celery import Celery
from celery.schedules import crontab

# 1. Set the default Django settings module for the 'celery' program.
# Replace 'core.settings' with your actual settings path (e.g., 'config.settings')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('uptimepulse')

# 2. Use 'django.conf:settings' (NOTICE: 'conf', NOT 'config'!)
app.config_from_object('django.conf:settings', namespace='CELERY')

# 3. Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'ping-all-sites-every-60-seconds': {
        'task': 'monitoring.tasks.ping_all_active_sites_task',
        'schedule': 60.0,  # Run every 60 seconds
    },
    'warm-site-metrics-cache-every-5-min':{
        'task': 'monitoring.tasks.update_all_site_metrics_cache_task',
        'schedule' : crontab(minute = '*/5'),
    },
    
}