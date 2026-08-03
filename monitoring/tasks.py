import time 
import httpx
from celery import shared_task

from django.utils import timezone
from .models import MonitoredSite, CheckLog, IncidentReport
from .utils import update_site_metrics_cache, get_consecutive_failures

from django.core.mail import send_mail

@shared_task
def ping_site_task(site_id):
    
    try:
        site = MonitoredSite.objects.get(id = site_id)
    except MonitoredSite.DoesNotExist:
        return f"Site with {site_id} not found."
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; x64) UptimePulse-Worker/1.0'
    }

    start_time = time.perf_counter()
    status_code  = None
    is_successful = False
    error_message = None
    
    try:
        response = httpx.get(site.url, 
                             headers=headers,
                             timeout= site.timeout_seconds,
                             follow_redirects= True
                             )
        response_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        status_code = response.status_code
        
        if status_code == site.expected_status_code:
            is_successful = True
        else:
            error_message = f"Expected HTTP {site.expected_status_code}, got {status_code}"
        
    except httpx.TimeoutException:
        response_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        error_message = f"Request time out after {response_time_ms} seconds"
        
    except httpx.RequestError as exc:
        response_time_ms  = round((time.perf_counter() - start_time)*1000, 2)
        error_message = f"Network connection error: {str(exc)}"
        
    except Exception as exc:
        response_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        error_message = f"Unexpected error: {str(exc)}"
        
    log = CheckLog.objects.create(site = site,
                                  status_code = status_code,
                                  response_time_ms = response_time_ms,
                                  is_successful = is_successful,
                                  error_message = error_message,
                                  )
    site.last_checked_at = timezone.now()
    # site.is_active = is_successful
    site.save(update_fields=['last_checked_at'])
    
    #Refresh redis cache imidiately with the latest metrics
    update_site_metrics_cache(site_id)
    
    if not is_successful:
        handle_incidents(log, error_message)
    
    return f"Pinged {site.url} | Status : {status_code} | Success: {is_successful}"

@shared_task
def ping_all_active_sites_task():
    
    active_sites = MonitoredSite.objects.filter(is_active = True)
    dispatched_count = 0
    
    for site in active_sites:
        ping_site_task.delay(site.id)
        dispatched_count += 1
    
    return f"Dispatched background check task for {dispatched_count} active sites"


def handle_incidents(log, error_message):
    site = log.site

    # 1. Require 3 consecutive failures before alerting
    if get_consecutive_failures(site.id, limit=3):
        
        # 2. Prevent duplicate open incidents for the same ongoing failure streak
        # (Adjust field filter if your model uses status='OPEN' or is_resolved=False)
        already_open = IncidentReport.objects.filter(
            check_log__site=site
        ).exists()

        if not already_open:
            report = IncidentReport.objects.create(
                check_log=log,
                summary=f"CRITICAL: 3 consecutive checks failed for {site.url}",
                confidence_score=0.9,
                possible_cause=str(error_message)[:255] if error_message else "Sustained connection failure",
                recommended_action="Inspect target server connectivity, HTTP status code, or network route.",
            )
            
            send_incident_alert_task.delay(str(report.id))
            
            
@shared_task
def update_all_site_metrics_cache_task():
    active_sites = MonitoredSite.objects.filter(is_active = True).values_list('id', flat= True)
    count = 0
    
    for site_id in active_sites:
        update_site_metrics_cache(site_id)
        count += 1
    
    return f"Successfully updated metrics cache for {count} sites."


@shared_task
def send_incident_alert_task(incident_report_id):
    
    try:
        report = IncidentReport.objects.select_related('check_log__site__user').get(id = incident_report_id)
        site = report.check_log.site
        user_email = site.user.email
        
        site_identifier = site.name if site.name else site.url
        subject = f"⚠️ ALERT: Incident Detected on {site_identifier}"

        # Safe datetime formatting with fallback if created_at is None
        formatted_time = (
            report.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')
            if getattr(report, 'created_at', None)
            else timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        )

        message = (
            f"Incident Alert Report\n"
            f"---------------------\n"
            f"Site Name:          {site.name or 'N/A'}\n"
            f"Site URL:           {site.url}\n"
            f"Summary:            {report.summary}\n"
            f"Possible Cause:     {report.possible_cause}\n"
            f"Confidence Score:   {report.confidence_score * 100:.0f}%\n"
            f"Recommended Action: {report.recommended_action}\n"
            f"Timestamp:          {formatted_time}\n"
        )
        send_mail(
            subject=subject,
            message= message,
            from_email="alert@uptimepulse.com",
            recipient_list= [user_email],
            fail_silently= False         
        )
        
        return f"Alert email sent to {user_email} for IncidentReport #{incident_report_id}"
    except IncidentReport.DoesNotExist:
        return f"IncidentReport #{incident_report_id} not found."