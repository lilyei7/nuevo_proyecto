from django.urls import path
from . import api_views

urlpatterns = [
    # Hotel API
    path('', api_views.HotelListAPIView.as_view(), name='api_hotel_list'),
    path('<int:pk>/', api_views.HotelDetailAPIView.as_view(), name='api_hotel_detail'),
    
    # Scraping API
    path('<int:pk>/scrape/', api_views.ScrapeHotelAPIView.as_view(), name='api_hotel_scrape'),
    path('bulk-scrape/', api_views.BulkScrapeAPIView.as_view(), name='api_bulk_scrape'),
    
    # OTASync API
    path('<int:pk>/sync-otasync/', api_views.SyncOTASyncAPIView.as_view(), name='api_hotel_sync_otasync'),
    path('bulk-sync/', api_views.BulkSyncAPIView.as_view(), name='api_bulk_sync'),
    
    # Results API
    path('<int:pk>/results/', api_views.ScrapingResultListAPIView.as_view(), name='api_scraping_results'),
]
