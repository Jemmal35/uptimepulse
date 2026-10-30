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
 
from rest_framework import serializers
from .models import IncidentReport


class IncidentReportSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='check_log.site.name', read_only=True)
    detected_at = serializers.DateTimeField(source='check_log.timestamp', read_only=True)
    status_code = serializers.IntegerField(source='check_log.status_code', read_only=True)
    error_message = serializers.CharField(source='check_log.error_message', read_only=True)
    recommended_actions = serializers.SerializerMethodField()
    confidence_score = serializers.SerializerMethodField()

    class Meta:
        model = IncidentReport
        fields = ['id', 'site_name', 'detected_at', 'status_code', 'error_message',
                  'summary', 'possible_cause', 'confidence_score',
                  'recommended_actions', 'is_ai_generated', 'created_at']

    def get_recommended_actions(self, obj):
        return [line.lstrip('- ').strip()
                for line in obj.recommended_action.splitlines() if line.strip()]

    def get_confidence_score(self, obj):
        # the fallback's 0.9 is a placeholder, so don't present it as a real score
        return obj.confidence_score if obj.is_ai_generated else None      
    
     
# class IncidentReportSerializer(serializers.ModelSerializer):
#     site_name = serializers.ReadOnlyField(source = 'check_log.site.name')
#     site_url = serializers.ReadOnlyField(source = 'check_log.site.url')
#     class Meta:
#         model = IncidentReport
#         fields = ('id', 'site_name', 'site_url', 'summary', 'confidence_score', 'possible_cause', 'recommended_action', 'created_at')