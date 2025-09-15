from django.urls import path
from . import views

urlpatterns = [
    # Hotel CRUD
    path('', views.HotelListView.as_view(), name='hotel_list'),
    path('create/', views.HotelCreateView.as_view(), name='hotel_create'),
    path('<int:pk>/', views.HotelDetailView.as_view(), name='hotel_detail'),
    path('<int:pk>/update/', views.HotelUpdateView.as_view(), name='hotel_update'),
    path('<int:pk>/delete/', views.HotelDeleteView.as_view(), name='hotel_delete'),
    
    # Hotel Actions
    path('<int:pk>/scrape/', views.ScrapeHotelView.as_view(), name='hotel_scrape'),
    path('<int:pk>/scrape-intelligent/', views.IndividualScrapeView.as_view(), name='hotel_scrape_intelligent'),
    path('<int:pk>/sync-otasync/', views.SyncOTASyncView.as_view(), name='hotel_sync_otasync'),
    path('<int:pk>/toggle-status/', views.ToggleHotelStatusView.as_view(), name='hotel_toggle_status'),
    
    # OTASync API
    path('otasync-properties/', views.OTASyncPropertiesView.as_view(), name='otasync_properties'),
    
    # Bulk Actions
    path('bulk/scrape/', views.BulkScrapeView.as_view(), name='hotel_bulk_scrape'),
    path('bulk/sync/', views.BulkSyncView.as_view(), name='hotel_bulk_sync'),
    path('bulk/update-status/', views.BulkUpdateStatusView.as_view(), name='hotel_bulk_update_status'),
    
    # Scraping Results
    path('<int:hotel_pk>/results/', views.ScrapingResultListView.as_view(), name='scraping_results'),
    path('results/<int:pk>/', views.ScrapingResultDetailView.as_view(), name='scraping_result_detail'),
    
    # Import/Export
    path('import/', views.ImportHotelsView.as_view(), name='hotel_import'),
    path('export/', views.ExportHotelsView.as_view(), name='hotel_export'),
]
