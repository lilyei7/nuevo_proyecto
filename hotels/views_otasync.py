from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
import json
from datetime import datetime, timedelta
from decimal import Decimal

from .models import Hotel, ScrapingResult
from django.contrib.auth.models import User

# Importar nuestro servicio de gestión
import sys
import os
sys.path.append('/home/gordon/Escritorio/scraping/nuevo_proyecto')

try:
    from hotel_management_service import HotelManagementService
    HOTEL_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Hotel Management Service no disponible: {e}")
    HOTEL_SERVICE_AVAILABLE = False


@login_required
def hotel_list(request):
    """Vista principal para listar hoteles"""
    hotels = Hotel.objects.all().order_by('-created_at')
    
    # Paginación
    paginator = Paginator(hotels, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'hotels': page_obj.object_list,
        'hotel_service_available': HOTEL_SERVICE_AVAILABLE,
    }
    
    return render(request, 'hotels/hotel_list.html', context)


@login_required 
def hotel_create(request):
    """Vista para crear nuevo hotel"""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            name = request.POST.get('name', '').strip()
            url = request.POST.get('url', '').strip()
            description = request.POST.get('description', '').strip()
            city = request.POST.get('city', '').strip()
            country = request.POST.get('country', '').strip()
            
            # Datos de OTASync
            otasync_property_id = request.POST.get('otasync_property_id', '').strip()
            otasync_pricing_plan_id = request.POST.get('otasync_pricing_plan_id', '').strip()
            otasync_room_type_id = request.POST.get('otasync_room_type_id', '').strip()
            otasync_sync_days = request.POST.get('otasync_sync_days', '20')
            
            # Validación básica
            if not name or not url:
                messages.error(request, 'Nombre y URL son requeridos')
                return render(request, 'hotels/hotel_create.html')
            
            # Usar el servicio si está disponible
            if HOTEL_SERVICE_AVAILABLE:
                service = HotelManagementService()
                hotel = service.register_hotel(
                    name=name,
                    booking_url=url,
                    otasync_property_id=otasync_property_id if otasync_property_id else None,
                    otasync_pricing_plan_id=otasync_pricing_plan_id if otasync_pricing_plan_id else None,
                    description=description,
                    city=city,
                    country=country
                )
            else:
                # Crear directamente si el servicio no está disponible
                hotel = Hotel.objects.create(
                    name=name,
                    url=url,
                    source="booking.com",
                    description=description,
                    city=city,
                    country=country,
                    otasync_property_id=otasync_property_id if otasync_property_id else None,
                    otasync_pricing_plan_id=otasync_pricing_plan_id if otasync_pricing_plan_id else None,
                    otasync_room_type_id=otasync_room_type_id if otasync_room_type_id else None,
                    otasync_sync_days=int(otasync_sync_days) if otasync_sync_days else 20,
                    otasync_enabled=bool(otasync_property_id and otasync_pricing_plan_id),
                    status='active',
                    created_by=request.user
                )
            
            if hotel:
                messages.success(request, f'Hotel "{name}" creado exitosamente')
                return redirect('hotels:hotel_detail', pk=hotel.id)
            else:
                messages.error(request, 'Error al crear el hotel')
                
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    # Valores por defecto para el formulario
    context = {
        'default_otasync_property_id': '9355',  # La propiedad que sabemos que funciona
        'default_otasync_pricing_plan_id': '26946',  # El pricing plan que funciona
        'default_sync_days': 20
    }
    
    return render(request, 'hotels/hotel_create.html', context)


@login_required
def hotel_detail(request, pk):
    """Vista de detalle de hotel"""
    hotel = get_object_or_404(Hotel, pk=pk)
    
    # Obtener resultados de scraping recientes
    recent_results = ScrapingResult.objects.filter(
        hotel=hotel
    ).order_by('-scraped_at')[:20]
    
    # Estadísticas
    total_results = ScrapingResult.objects.filter(hotel=hotel).count()
    successful_results = ScrapingResult.objects.filter(hotel=hotel, success=True).count()
    
    context = {
        'hotel': hotel,
        'recent_results': recent_results,
        'total_results': total_results,
        'successful_results': successful_results,
        'success_rate': (successful_results / total_results * 100) if total_results > 0 else 0,
        'hotel_service_available': HOTEL_SERVICE_AVAILABLE,
    }
    
    return render(request, 'hotels/hotel_detail.html', context)


@login_required
@require_http_methods(["POST"])
def hotel_run_scraping(request, pk):
    """Ejecutar scraping para un hotel específico"""
    hotel = get_object_or_404(Hotel, pk=pk)
    
    if not HOTEL_SERVICE_AVAILABLE:
        return JsonResponse({
            'success': False,
            'error': 'Hotel Management Service no disponible'
        })
    
    try:
        # Obtener parámetros
        days = int(request.POST.get('days', 20))
        
        # Ejecutar scraping
        service = HotelManagementService()
        results = service.scrape_hotel_prices(hotel, days=days)
        
        successful_count = len([r for r in results if r.get('success')])
        
        return JsonResponse({
            'success': True,
            'message': f'Scraping completado: {successful_count}/{len(results)} exitosos',
            'results_count': len(results),
            'successful_count': successful_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def hotel_sync_otasync(request, pk):
    """Sincronizar precios con OTASync"""
    hotel = get_object_or_404(Hotel, pk=pk)
    
    if not hotel.otasync_enabled:
        return JsonResponse({
            'success': False,
            'error': 'OTASync no está habilitado para este hotel'
        })
    
    if not HOTEL_SERVICE_AVAILABLE:
        return JsonResponse({
            'success': False,
            'error': 'Hotel Management Service no disponible'
        })
    
    try:
        service = HotelManagementService()
        
        # Verificar si usar precios del scraping o precio fijo
        use_scraped_prices = request.POST.get('use_scraped_prices') == 'true'
        
        success = service.sync_prices_to_otasync(hotel, use_scraped_prices=use_scraped_prices)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'Precios sincronizados exitosamente con OTASync'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Error al sincronizar con OTASync'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def hotel_full_workflow(request, pk):
    """Ejecutar workflow completo: Scraping + Sincronización"""
    hotel = get_object_or_404(Hotel, pk=pk)
    
    if not HOTEL_SERVICE_AVAILABLE:
        return JsonResponse({
            'success': False,
            'error': 'Hotel Management Service no disponible'
        })
    
    try:
        # Obtener parámetros
        scraping_days = int(request.POST.get('scraping_days', 20))
        
        # Ejecutar workflow completo
        service = HotelManagementService()
        workflow_result = service.full_hotel_workflow(hotel, scraping_days=scraping_days)
        
        return JsonResponse({
            'success': workflow_result.get('success', False),
            'message': workflow_result.get('message', ''),
            'scraping_count': workflow_result.get('scraping_count', 0),
            'otasync_synced': workflow_result.get('otasync_synced', False)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def hotel_results(request, pk):
    """Vista de resultados de scraping para un hotel"""
    hotel = get_object_or_404(Hotel, pk=pk)
    
    # Filtros
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status_filter = request.GET.get('status', '')
    
    # Query base
    results_query = ScrapingResult.objects.filter(hotel=hotel)
    
    # Aplicar filtros
    if date_from:
        try:
            date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
            results_query = results_query.filter(check_in__gte=date_from_parsed)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
            results_query = results_query.filter(check_in__lte=date_to_parsed)
        except ValueError:
            pass
    
    if status_filter:
        if status_filter == 'success':
            results_query = results_query.filter(success=True)
        elif status_filter == 'failed':
            results_query = results_query.filter(success=False)
    
    # Ordenar por fecha de check-in más reciente
    results = results_query.order_by('-check_in', '-scraped_at')
    
    # Paginación
    paginator = Paginator(results, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'hotel': hotel,
        'page_obj': page_obj,
        'results': page_obj.object_list,
        'date_from': date_from,
        'date_to': date_to,
        'status_filter': status_filter,
    }
    
    return render(request, 'hotels/hotel_results.html', context)


@login_required
def dashboard_home(request):
    """Dashboard principal"""
    # Estadísticas generales
    total_hotels = Hotel.objects.count()
    active_hotels = Hotel.objects.filter(status='active').count()
    otasync_enabled_hotels = Hotel.objects.filter(otasync_enabled=True).count()
    
    # Resultados recientes
    recent_results = ScrapingResult.objects.order_by('-scraped_at')[:10]
    
    # Hoteles con sync reciente
    recently_synced = Hotel.objects.filter(
        last_sync__gte=timezone.now() - timedelta(hours=24)
    ).order_by('-last_sync')[:5]
    
    context = {
        'total_hotels': total_hotels,
        'active_hotels': active_hotels,
        'otasync_enabled_hotels': otasync_enabled_hotels,
        'recent_results': recent_results,
        'recently_synced': recently_synced,
        'hotel_service_available': HOTEL_SERVICE_AVAILABLE,
    }
    
    return render(request, 'hotels/dashboard.html', context)
