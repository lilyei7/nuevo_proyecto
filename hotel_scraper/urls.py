"""
URL configuration for hotel_scraper project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Authentication
    path('auth/', include('authentication.urls')),
    
    # Apps
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),  # Redirigir al dashboard
    path('dashboard/', include('dashboard.urls')),
    path('hotels/', include('hotels.urls')),  # URLs de hoteles
    # path('hotels/api/', include('hotels.api_urls')),  # API URLs para hoteles
    # path('otasync/', include('hotels.urls_otasync')),  # Nuevas rutas de OTASync
    
    # Calendario Kunas
    # path('calendario/', include('kunas_calendar_urls')),  # URLs del calendario - comentado
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
