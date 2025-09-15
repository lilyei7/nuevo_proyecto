from django.urls import path
from . import views, realtime_views
from .simple_sse import SimpleSSEView, TestWebhookView
from .sse_fixed import FixedSSEView, SimpleHealthCheckView, SSETestView as FixedSSETestView
from .views_sse import SSETestView
# from .debug_sse import DebugSSEView  # Archivo no existe
DebugSSEView = None
# Importación condicional para MiniSSEView
try:
    from .views_simplesse import MiniSSEView
except ImportError:
    MiniSSEView = None
from .views_otasync import (
    OTASyncStatusView, 
    OTASyncPropertiesView, 
    OTASyncTestConnectionView, 
    OTASyncBulkSyncView
)

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Statistics
    path('stats/', views.StatsView.as_view(), name='dashboard_stats'),
    path('stats/api/', views.StatsAPIView.as_view(), name='dashboard_stats_api'),
    
    # System
    path('system/', views.SystemStatusView.as_view(), name='system_status'),
    path('logs/', views.LogsView.as_view(), name='system_logs'),
    
    # Monitor
    path('monitor/', views.DashboardMonitorView.as_view(), name='dashboard_monitor'),
    path('monitor/integrated/', views.IntegratedMonitorView.as_view(), name='integrated_monitor'),
    path('monitor/realtime/', views.RealtimeMonitorView.as_view(), name='realtime_monitor'),
    path('sse-test/', views.SSETestPageView.as_view(), name='sse_test_page'),
    path('test-sse/', SSETestView.as_view(), name='sse_test'),
    
    # Realtime Events (SSE)
    path('sse/', FixedSSEView.as_view(), name='main_sse'),  # Endpoint SSE corregido
    path('sse/fixed/', FixedSSEView.as_view(), name='fixed_sse'),  # SSE corregido
    path('sse/test/', FixedSSETestView.as_view(), name='sse_test_fixed'),  # Test SSE simple
    path('sse/original/', SimpleSSEView.as_view(), name='original_sse'),  # SSE original para comparar
    path('health/', SimpleHealthCheckView.as_view(), name='health_check'),  # Health check
    path('monitor/events/', realtime_views.RealtimeEventsView.as_view(), name='realtime_events'),
    path('simple-sse/', SimpleSSEView.as_view(), name='simple_sse'),
    # path('debug-sse/', DebugSSEView.as_view(), name='debug_sse'),  # Vista no existe
    path('mini-sse/', MiniSSEView.as_view() if MiniSSEView else SimpleSSEView.as_view(), name='mini_sse'),
    path('webhook/scraping-event/', realtime_views.ScrapingEventWebhookView.as_view(), name='scraping_webhook'),
    
    # Scraping Results
    path('results/', views.ScrapingResultsView.as_view(), name='scraping_results'),
    path('results/api/', views.ScrapingResultsAPIView.as_view(), name='scraping_results_api'),
    
    # Scraping Control API
    path('api/start-scraping/', views.StartScrapingAPIView.as_view(), name='start_scraping_api'),
    path('api/stop-scraping/', views.StopScrapingAPIView.as_view(), name='stop_scraping_api'),
    
    # Real-time Logs API
    path('api/logs/', views.RealTimeLogsAPIView.as_view(), name='realtime_logs_api'),
    path('api/logs/clear/', views.ClearLogsAPIView.as_view(), name='clear_logs_api'),
    
    # OTASync Integration
    path('otasync/status/', OTASyncStatusView.as_view(), name='otasync_status'),
    path('otasync/properties/', OTASyncPropertiesView.as_view(), name='otasync_properties'),
]
