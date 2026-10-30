from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (MonitoredSiteListCreateView, MonitoredSiteDetailView, ManualCheckApiView, IncidentReportListView, SiteMetricsDetailView,
                    SiteChartDataView)


urlpatterns = [
    # Auth Endpoints (JWT)
    path('auth/token/', TokenObtainPairView.as_view(), name= 'token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name= 'token_refresh'),
    
    #Site Endpoints
    path('sites/', MonitoredSiteListCreateView.as_view(), name= 'site-list-create'),
    path('sites/<uuid:pk>/', MonitoredSiteDetailView.as_view(), name= 'site-detail'),
    path('sites/<uuid:pk>/check/', ManualCheckApiView.as_view(), name= 'site-manual-check'),
    path('sites/incidents/',IncidentReportListView.as_view(), name= 'site-incident-list'),
    path('sites/<uuid:site_id>/incidents/', IncidentReportListView.as_view(), name='site-incidents'),
    path('site/<uuid:site_id>/metrics/', SiteMetricsDetailView.as_view(), name= 'site-metrics-detail'),
    path('site/<uuid:site_id>/chart-data/', SiteChartDataView.as_view(), name= 'site-chart-data')
]


