from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from otasync_integration import otasync_integration
import json
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
def test_otasync_connection(request):
    """Endpoint para probar la conexión con OTASync"""
    try:
        # Probar conexión
        connected = otasync_integration.test_connection()
        
        if connected:
            # Obtener estado
            status = otasync_integration.get_sync_status()
            
            return JsonResponse({
                'success': True,
                'connected': connected,
                'status': status,
                'message': '✅ OTASync conectado exitosamente'
            })
        else:
            return JsonResponse({
                'success': False,
                'connected': False,
                'message': '❌ Error conectando a OTASync'
            })
    
    except Exception as e:
        logger.error(f"Error en test_otasync_connection: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': f'❌ Error: {e}'
        })


@login_required
def sync_hotel_prices(request):
    """Endpoint para sincronizar precios de hoteles con OTASync"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        from hotels.models import ScrapingResult
        
        # Obtener resultados de scraping no sincronizados
        pending_results = ScrapingResult.objects.filter(
            otasync_synced=False,
            hotel__otasync_enabled=True,
            status='success',
            price__isnull=False
        )[:10]  # Limitar a 10 para pruebas
        
        if not pending_results:
            return JsonResponse({
                'success': True,
                'message': 'No hay precios pendientes de sincronizar',
                'sync_stats': {
                    'total': 0,
                    'success': 0,
                    'failed': 0,
                    'skipped': 0
                }
            })
        
        # Sincronizar precios
        sync_stats = otasync_integration.bulk_sync_prices(pending_results)
        
        return JsonResponse({
            'success': True,
            'message': f'Sincronización completada: {sync_stats["success"]} éxitos de {sync_stats["total"]} total',
            'sync_stats': sync_stats
        })
    
    except Exception as e:
        logger.error(f"Error en sync_hotel_prices: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': f'❌ Error sincronizando precios: {e}'
        })


def otasync_status_view(request):
    """Vista para mostrar el estado de OTASync"""
    try:
        from hotels.models import Hotel
        
        context = {
            'otasync_integration': otasync_integration,
            'total_hotels': Hotel.objects.count(),
            'otasync_enabled_hotels': Hotel.objects.filter(otasync_enabled=True).count(),
        }
        
        # Intentar obtener estado completo
        try:
            context['sync_status'] = otasync_integration.get_sync_status()
        except Exception as e:
            context['sync_status'] = {'error': str(e)}
        
        return render(request, 'dashboard/otasync_status.html', context)
    
    except Exception as e:
        logger.error(f"Error en otasync_status_view: {e}")
        return render(request, 'dashboard/otasync_status.html', {
            'error': str(e)
        })
