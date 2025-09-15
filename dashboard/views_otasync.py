from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils import timezone
from hotels.models import Hotel, ScrapingResult
from otasync_integration import otasync_integration
import json


class OTASyncStatusView(LoginRequiredMixin, TemplateView):
    """Vista de estado de OTASync"""
    template_name = 'dashboard/otasync_status.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener estado de OTASync
        sync_status = otasync_integration.get_sync_status()
        context['sync_status'] = sync_status
        
        # Hoteles con OTASync habilitado
        context['otasync_hotels'] = Hotel.objects.filter(otasync_enabled=True)
        
        # Estadísticas de sincronización
        context['sync_stats'] = {
            'total_hotels': Hotel.objects.count(),
            'otasync_enabled': Hotel.objects.filter(otasync_enabled=True).count(),
            'pending_sync': ScrapingResult.objects.filter(
                otasync_synced=False,
                hotel__otasync_enabled=True,
                status='success'
            ).count()
        }
        
        return context


class OTASyncPropertiesView(LoginRequiredMixin, TemplateView):
    """Vista de propiedades de OTASync"""
    template_name = 'dashboard/otasync_properties.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener propiedades de OTASync
        try:
            properties = otasync_integration.get_properties()
            context['properties'] = properties
            context['properties_count'] = len(properties)
        except Exception as e:
            context['properties'] = []
            context['properties_count'] = 0
            context['error'] = str(e)
        
        return context


class OTASyncTestConnectionView(LoginRequiredMixin, TemplateView):
    """API para probar conexión con OTASync"""
    
    def get(self, request, *args, **kwargs):
        try:
            # Probar conexión
            is_connected = otasync_integration.test_connection()
            
            # Obtener estado completo
            status = otasync_integration.get_sync_status()
            
            return JsonResponse({
                'success': True,
                'connected': is_connected,
                'status': status,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=500)


class OTASyncBulkSyncView(LoginRequiredMixin, TemplateView):
    """Vista para sincronización masiva con OTASync"""
    
    def post(self, request, *args, **kwargs):
        try:
            # Obtener resultados pendientes de sincronización
            pending_results = ScrapingResult.objects.filter(
                otasync_synced=False,
                hotel__otasync_enabled=True,
                status='success',
                price__isnull=False
            )[:50]  # Limitar a 50 para no sobrecargar
            
            # Realizar sincronización masiva
            sync_stats = otasync_integration.bulk_sync_prices(pending_results)
            
            return JsonResponse({
                'success': True,
                'sync_stats': sync_stats,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=500)
