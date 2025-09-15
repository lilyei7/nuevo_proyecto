from django.urls import path
from . import views_otasync

app_name = 'hotels_otasync'

urlpatterns = [
    # Dashboard
    path('', views_otasync.dashboard_home, name='dashboard'),
    
    # Hotel Management
    path('hotels/', views_otasync.hotel_list, name='hotel_list'),
    path('hotels/create/', views_otasync.hotel_create, name='hotel_create'),
    path('hotels/<int:pk>/', views_otasync.hotel_detail, name='hotel_detail'),
    path('hotels/<int:pk>/results/', views_otasync.hotel_results, name='hotel_results'),
    
    # Hotel Actions (AJAX endpoints)
    path('hotels/<int:pk>/scrape/', views_otasync.hotel_run_scraping, name='hotel_scrape'),
    path('hotels/<int:pk>/sync/', views_otasync.hotel_sync_otasync, name='hotel_sync'),
    path('hotels/<int:pk>/workflow/', views_otasync.hotel_full_workflow, name='hotel_workflow'),
]
