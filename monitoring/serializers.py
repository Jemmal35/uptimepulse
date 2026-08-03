from rest_framework import serializers
from .models import User, MonitoredSite, CheckLog, IncidentReport

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields =  ('id', 'email', 'username')
        
class MonitoredSiteSerializer(serializers.ModelSerializer):
    # Read-only field so the site owner is automatically assigned from the JWT request user
    user = serializers.ReadOnlyField(source = 'user.email')
    
    class Meta:
        model = MonitoredSite
        fields = ('id', 'user', 'name', 'url', 'check_interval', 'expected_status_code', 'timeout_seconds', 'is_active', 'created_at')

               
class CheckLogSerializer(serializers.ModelSerializer):
    site_name = serializers.ReadOnlyField(source = 'site.name')
    
    class Meta:
        model = CheckLog
        fields = ('id', 'site_name', 'status_code', 'response_time_ms', 'is_successful', 'error_message','timestamp')
        
class IncidentReportSerializer(serializers.ModelSerializer):
    site_name = serializers.ReadOnlyField(source = 'check_log.site.name')
    site_url = serializers.ReadOnlyField(source = 'check_log.site.url')
    class Meta:
        model = IncidentReport
        fields = ('id', 'site_name', 'site_url', 'summary', 'confidence_score', 'possible_cause', 'recommended_action', 'created_at')