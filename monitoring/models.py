import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key= True, default= uuid.uuid4, editable= False)
    email = models.EmailField(unique= True)
    is_asctive = models.BooleanField(default= True)
    created_at = models.DateTimeField(auto_now_add= True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    
    
class MonitoredSite(models.Model):
    id = models.UUIDField(primary_key= True, default= uuid.uuid4, editable= False)
    user = models.ForeignKey(User, on_delete= models.CASCADE, related_name= 'sites')
    name = models.CharField(max_length= 100)
    url = models.URLField(db_index= True)
    check_interval = models.IntegerField(default= 60)
    last_checked_at = models.DateTimeField(auto_now_add= True)
    expected_status_code = models.IntegerField(default= 200)
    timeout_seconds = models.IntegerField(default= 10)
    is_active = models.BooleanField(default= True)
    created_at = models.DateTimeField(auto_now_add= True)
    
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return f'{self.name} ({self.url})'
    
    
class CheckLog(models.Model):
    id = models.BigAutoField(primary_key= True)
    site = models.ForeignKey(MonitoredSite, on_delete= models.CASCADE, related_name= 'logs')
    status_code = models.IntegerField(null= True, blank= True)
    response_time_ms = models.FloatField(null= True, blank= True)
    is_successful = models.BooleanField(db_index= True)
    error_message = models.TextField(blank= True, null= True, default= '')
    timestamp = models.DateTimeField(auto_now_add= True, db_index= True)
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        status = "UP" if self.is_successful else "DOWN"
        return f'{self.site.name} - {status} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}'
    
    
class IncidentReport(models.Model):
    id = models.UUIDField(primary_key= True, default= uuid.uuid4, editable= False)
    check_log = models.OneToOneField(CheckLog,  on_delete= models.CASCADE, related_name= 'ai_report')
    summary = models.TextField()
    ai_analysis = models.JSONField(null=True, blank=True)
    ai_analyzed_at = models.DateTimeField(null=True, blank=True)
    is_ai_generated = models.BooleanField(default=False)
    confidence_score = models.FloatField()
    possible_cause = models.CharField(max_length= 255)
    recommended_action = models.TextField()
    created_at = models.DateTimeField(auto_now_add= True)
    
    def __str__(self):
        return f'Incedent AI Report for Log #{self.check_log.id} ({self.possible_cause})'