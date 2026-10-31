from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg, Q, Count
from django.core.cache import cache
from .models import CheckLog


def update_site_metrics_cache(site_id):
    """
    Calculates 24-hour performance metrics for a specific site 
    and saves the dictionary directly into Redis DB 0.
    """
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    
    # 1. Aggregate stats from CheckLog
    stats = CheckLog.objects.filter(
        site_id=site_id, 
        timestamp__gte=last_24h
    ).aggregate(
        total_checks=Count('id'),
        successful_checks=Count('id', filter=Q(is_successful=True)),
        avg_response_time=Avg('response_time_ms')
    )
    
    # 2. Prevent NoneType crashes when zero logs exist
    total = stats['total_checks'] or 0
    successful = stats['successful_checks'] or 0
    avg_time = stats['avg_response_time']
    if avg_time is None:
        avg_time = 0.0
    
    uptime_percentage = ((successful / total) * 100) if total > 0 else 100.0
    
    metrics_data = {
        'uptime_percentage': round(uptime_percentage, 2),
        'avg_response_time': round(avg_time, 2),
        'total_checks_24h': total,
        'last_updated': now.isoformat()
    }
    
    # 3. Use stringified UUID key
    cache_key = f'site_metrics:{str(site_id)}'
    
    # Cache for 10 minutes in DB 0
    cache.set(cache_key, metrics_data, timeout=600)
    
    return metrics_data
    

def get_consecutive_failures(site_id, limit=3):
    """
    Checks the last `limit` logs for a site.
    Returns True if ALL of the last `limit` logs were failures.
    """
    recent_logs = CheckLog.objects.filter(
        site_id=site_id
    ).order_by('-timestamp')[:limit]

    # If we don't have 3 logs recorded yet, don't trigger an incident
    if len(recent_logs) < limit:
        return False

    return all(not log.is_successful for log in recent_logs)