from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, MonitoredSite, CheckLog, IncidentReport

admin.site.register(User, UserAdmin)

@admin.register(MonitoredSite)
class MonitoredSiteAdmin(admin.ModelAdmin):
    list_display = ('name','url', 'user','is_active', 'check_interval', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'url', 'user__email')
    
@admin.register(CheckLog)
class CheckLogAdmin(admin.ModelAdmin):
    list_display = ('site', 'is_successful','status_code', 'response_time_ms', 'timestamp')
    list_filter = ('is_successful', 'timestamp')
    search_fields = ('site__name', 'site_url', 'error_message') 

@admin.register(IncidentReport)
class IncedentReportAdmin(admin.ModelAdmin):
    list_display = ('check_log', 'possible_cause', 'confidence_score', 'created_at')
    search_fields = ('possible_cause', 'summary')