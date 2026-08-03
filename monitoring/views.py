import time
import httpx
from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg
from django.utils import timezone
from django.db.models.functions import TruncHour

from .models import User, MonitoredSite, CheckLog, IncidentReport

from .serializers import UserSerializer, MonitoredSiteSerializer, CheckLogSerializer, IncidentReportSerializer  
from .tasks import update_site_metrics_cache

class MonitoredSiteListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        sites = MonitoredSite.objects.filter(user = request.user).order_by('-created_at')
        total_count = sites.count()
        active_count = sites.filter(is_active = True).count()
        inactive_count = total_count - active_count
        
        serializer = MonitoredSiteSerializer(sites, many = True)
        context = {
                    "total_sites": total_count,
                    "total_active_sites": total_count,
                    "total_inactive_sites": inactive_count,
                    "sites" : serializer.data
                }
        
        return Response(context, status=status.HTTP_200_OK)
        
    def post(self, request):
        serializer = MonitoredSiteSerializer(data=request.data)
        if serializer.is_valid():
            # Explicitly attach the authenticated user as owner
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MonitoredSiteDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, pk, user):
        return get_object_or_404(MonitoredSite, id = pk, user = user)
    

    def get(self, request, pk):
        site = self.get_object(pk, request.user)
        serializer = MonitoredSiteSerializer(site)
        return Response(serializer.data, status= status.HTTP_200_OK)
    
    def put(self, request, pk):
        site = self.get_object(pk, request.user)
        serializer = MonitoredSiteSerializer(site, data= request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status= status.HTTP_200_OK)
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        site = self.get_object(pk, request.user)
        serializer = MonitoredSiteSerializer(site, data = request.data, partial = True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status= status.HTTP_200_OK)
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        site = self.get_object(pk, request.user)
        site.delete()
        return Response({'message':"Site deleted successfully."},   status= status.HTTP_204_NO_CONTENT)
        
        
class ManualCheckApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        site = get_object_or_404(MonitoredSite, pk = pk, user = request.user)
        start_time = time.time()
        status_code = None
        error_message = ''
        is_successful = False
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) UptimePulse/1.0'
        }
        headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
        try:
            response = httpx.get(
                site.url, 
                headers=headers, 
                timeout=site.timeout_seconds, 
                follow_redirects=True
            )
            # response = httpx.get(site.url, timeout=site.timeout_seconds, follow_redirects= True)
            status_code = response.status_code
            
            if status_code == site.expected_status_code:
                is_successful = True
            else:
                error_message = f"Expected HTTP {site.expected_status_code}, got {status_code}"
        except httpx.TimeoutException:
            error_message = f"Request timed out after {site.timeout_seconds} seconds"
        except httpx.RequestError as exc:
            error_message = f"Network connection error: {str(exc)}"
        except Exception as exc:
            f"Unexpected error: {str(exc)}"
            
        response_time_ms = round((time.time()-start_time)*1000, 2)
        
        log = CheckLog.objects.create(site = site, status_code = status_code, response_time_ms = response_time_ms if status_code else None, error_message = error_message, is_successful = is_successful)
        
        serializer = CheckLogSerializer(log)
        return Response(serializer.data, status= status.HTTP_201_CREATED)


class IncidentReportListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        incidents = IncidentReport.objects.filter(check_log__site__user = user).order_by('-created_at')
        serializer = IncidentReportSerializer(incidents, many = True)
        return Response(serializer.data, status= status.HTTP_200_OK)
    

    
class SiteMetricsDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, site_id):
        site = get_object_or_404(MonitoredSite, id=site_id, user=request.user)

        cache_key = f"site_metrics:{str(site.id)}"
        metrics = cache.get(cache_key)

        if not metrics:
            metrics = update_site_metrics_cache(site.id)

        return Response(
            {
                "site_id": str(site.id),
                "site_name": site.name,
                "metrics": metrics,
            },
            status=status.HTTP_200_OK,
        )
        

class SiteChartDataView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, site_id):
        site = get_object_or_404(MonitoredSite, id= site_id, user = request.user)
        
        last_24h = timezone.now() - timedelta(hours= 24)
        
        hourly_stats = (
            CheckLog.objects.filter(site = site, timestamp__gte = last_24h)
            .annotate(hour = TruncHour('timestamp'))
            .values('hour')
            .annotate(avg_response_time = Avg('response_time_ms'))
            .order_by('hour')
        )
        
        chart_data = [
            {
                "timestamp": entry['hour'].strftime('%H:00'),
                "avg_response_time": round(entry['avg_response_time'] or 0.0)
            }
            for entry in hourly_stats
        ]
        
        return Response({
            "site_id": str(site.id),
            "site_name": site.name,
            "data_points": len(chart_data),
            "series": chart_data
        }, status= status.HTTP_200_OK)