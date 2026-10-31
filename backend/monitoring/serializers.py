from rest_framework import serializers
from .models import User, MonitoredSite, CheckLog, IncidentReport
import ipaddress
import socket
from urllib.parse import urlparse
from django.conf import settings

from django.contrib.auth.password_validation import validate_password


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'password')

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields =  ('id', 'email', 'username')
        
class MonitoredSiteSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.email')
    check_interval = serializers.IntegerField(min_value=60, max_value=86400, required=False)
    timeout_seconds = serializers.IntegerField(min_value=1, max_value=30, required=False)
    expected_status_code = serializers.IntegerField(min_value=100, max_value=599, required=False)

    # filled by the list view's annotations; null for sites that have never been checked
    latest_is_up = serializers.BooleanField(read_only=True, allow_null=True)
    latest_response_ms = serializers.FloatField(read_only=True, allow_null=True)
    latest_status_code = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = MonitoredSite
        fields = ('id', 'user', 'name', 'url', 'check_interval', 'expected_status_code',
                  'timeout_seconds', 'is_active', 'created_at', 'last_checked_at',
                  'latest_is_up', 'latest_response_ms', 'latest_status_code')
        read_only_fields = ('last_checked_at',)

    def validate_url(self, value):
        if settings.DEBUG:      # lets you test with local or unresolvable demo URLs
            return value
        host = urlparse(value).hostname
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            raise serializers.ValidationError("Host could not be resolved.")
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise serializers.ValidationError("Private or internal addresses are not allowed.")
        return value

               
class CheckLogSerializer(serializers.ModelSerializer):
    site_name = serializers.ReadOnlyField(source = 'site.name')
    
    class Meta:
        model = CheckLog
        fields = ('id', 'site_name', 'status_code', 'response_time_ms', 'is_successful', 'error_message','timestamp')
 
from rest_framework import serializers
from .models import IncidentReport


class IncidentReportSerializer(serializers.ModelSerializer):
    site_id = serializers.UUIDField(source='check_log.site.id', read_only=True)
    site_url = serializers.CharField(source='check_log.site.url', read_only=True)
    site_name = serializers.CharField(source='check_log.site.name', read_only=True)
    detected_at = serializers.DateTimeField(source='check_log.timestamp', read_only=True)
    status_code = serializers.IntegerField(source='check_log.status_code', read_only=True)
    error_message = serializers.CharField(source='check_log.error_message', read_only=True)
    recommended_actions = serializers.SerializerMethodField()
    confidence_score = serializers.SerializerMethodField()

    class Meta:
        model = IncidentReport
        fields = ['id', 'site_id', 'site_url', 'site_name', 'detected_at', 'status_code', 'error_message',
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