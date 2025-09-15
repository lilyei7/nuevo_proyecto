from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Hotel, ScrapingResult
import os
import requests
import logging
import threading

log = logging.getLogger(__name__)
import sys


def fetch_otasync_properties():
    """
    Obtener propiedades disponibles de OTASync
    Retorna una lista de diccionarios {'id': str, 'name': str, 'pricing_plans': []}
    """
    try:
        print(f"🧪 fetch_otasync_properties: Iniciando...")
        from otasync_price_manager import OTASyncPriceManager
        
        manager = OTASyncPriceManager()
        print(f"🧪 Manager creado: {manager}")
        print(f"🧪 Auth data exists: {bool(manager.auth_data)}")
        
        if not manager.auth_data:
            print(f"❌ No hay auth_data disponible")
            return []
        
        # Obtener propiedades del auth_data
        properties = []
        if 'properties' in manager.auth_data:
            print(f"🧪 Properties key found in auth_data")
            props_data = manager.auth_data['properties']
            print(f"🧪 Raw properties data: {props_data}")
            
            for prop_data in props_data:
                prop_id = prop_data.get('id_properties', '')
                prop_name = prop_data.get('name', f'Propiedad {prop_id}')
                
                prop_dict = {
                    'id': str(prop_id),
                    'name': prop_name,
                    'pricing_plans': []  # Podríamos expandir esto en el futuro
                }
                properties.append(prop_dict)
                print(f"✅ Property added: {prop_dict}")
        else:
            print(f"❌ No 'properties' key in auth_data. Keys: {list(manager.auth_data.keys())}")
        
        print(f"🧪 Final properties list: {properties}")
        return properties
    except Exception as e:
        print(f"❌ Error in fetch_otasync_properties: {e}")
        import traceback
        traceback.print_exc()
        log.error(f"Error obteniendo propiedades OTASync: {e}")
        return []


class OTASyncPropertiesView(LoginRequiredMixin, View):
    """Vista AJAX para obtener propiedades de OTASync"""
    
    def get(self, request):
        properties = fetch_otasync_properties()
        return JsonResponse({'properties': properties})


class HotelListView(LoginRequiredMixin, ListView):
    """List all hotels"""
    model = Hotel
    template_name = 'hotels/hotel_list.html'
    context_object_name = 'hotels'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Hotel.objects.all()
        
        # Search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        # Status filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')


class HotelDetailView(LoginRequiredMixin, DetailView):
    """Hotel detail view"""
    model = Hotel
    template_name = 'hotels/hotel_detail.html'
    context_object_name = 'hotel'


class HotelCreateView(LoginRequiredMixin, CreateView):
    """Create new hotel"""
    model = Hotel
    template_name = 'hotels/hotel_form.html'
    fields = ['name', 'source', 'url', 'description', 'price_percent', 'status', 'otasync_enabled', 'otasync_property_id', 'otasync_pricing_plan_id', 'otasync_sync_days']
    success_url = reverse_lazy('hotel_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        # Normalize URL: strip common tracking query parameters to keep URL compact for scraping
        try:
            from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
            parsed = urlparse(form.instance.url or '')
            if parsed.scheme and parsed.netloc:
                qs = dict(parse_qsl(parsed.query, keep_blank_values=True))
                # Remove common tracking params
                for p in ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'ref', 'fbclid', 'gclid']:
                    qs.pop(p, None)
                new_q = urlencode(qs, doseq=True)
                form.instance.url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_q, parsed.fragment))
        except Exception:
            pass
        response = super().form_valid(form)
        messages.success(self.request, f'Hotel {form.instance.name} creado exitosamente.')

        # After creating the hotel, if OTASync is enabled, prepare for price synchronization
        try:
            if form.instance.otasync_enabled and form.instance.otasync_property_id:
                # Initialize OTASync integration for this hotel
                messages.info(self.request, f'OTASync configurado para {form.instance.otasync_property_id} con plan {form.instance.otasync_pricing_plan_id}')
        except Exception:
            # Non-fatal: we simply don't auto-assign if any error occurs
            pass

        return response

    def get_context_data(self, **kwargs):
        print(f"🧪 HotelCreateView.get_context_data: Iniciando...")
        context = super().get_context_data(**kwargs)
        # Incluir propiedades OTASync para el formulario
        otasync_properties = fetch_otasync_properties()
        print(f"🧪 Properties fetched in context: {otasync_properties}")
        context['otasync_properties'] = otasync_properties
        print(f"🧪 Context keys: {list(context.keys())}")
        return context


class HotelUpdateView(LoginRequiredMixin, UpdateView):
    """Update hotel"""
    model = Hotel
    template_name = 'hotels/hotel_form.html'
    fields = ['name', 'source', 'url', 'description', 'price_percent', 'status', 'otasync_enabled', 'otasync_property_id', 'otasync_pricing_plan_id', 'otasync_sync_days']
    success_url = reverse_lazy('hotel_list')
    
    def form_valid(self, form):
        # Normalize URL before saving update
        try:
            from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
            parsed = urlparse(form.instance.url or '')
            if parsed.scheme and parsed.netloc:
                qs = dict(parse_qsl(parsed.query, keep_blank_values=True))
                for p in ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'ref', 'fbclid', 'gclid']:
                    qs.pop(p, None)
                new_q = urlencode(qs, doseq=True)
                form.instance.url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_q, parsed.fragment))
        except Exception:
            pass
        response = super().form_valid(form)
        messages.success(self.request, f'Hotel {form.instance.name} actualizado exitosamente.')

        # OTASync integration for price updates - simplified since OTASync doesn't need room type lookup
        try:
            if form.instance.otasync_enabled and form.instance.otasync_property_id:
                messages.info(self.request, f'OTASync actualizado - Property: {form.instance.otasync_property_id}, Plan: {form.instance.otasync_pricing_plan_id}')
        except Exception:
            pass

        return response

    def get_context_data(self, **kwargs):
        print(f"🧪 HotelUpdateView.get_context_data: Iniciando...")
        context = super().get_context_data(**kwargs)
        # Incluir propiedades OTASync para el formulario
        otasync_properties = fetch_otasync_properties()
        print(f"🧪 Properties fetched in UPDATE context: {otasync_properties}")
        context['otasync_properties'] = otasync_properties
        print(f"🧪 UPDATE Context keys: {list(context.keys())}")
        return context


class HotelDeleteView(LoginRequiredMixin, DeleteView):
    """Delete hotel"""
    model = Hotel
    template_name = 'hotels/hotel_confirm_delete.html'
    success_url = reverse_lazy('hotel_list')
    
    def delete(self, request, *args, **kwargs):
        hotel = self.get_object()
        messages.success(request, f'Hotel {hotel.name} eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)


class ScrapeHotelView(LoginRequiredMixin, View):
    """Scrape a single hotel"""
    
    def post(self, request, pk):
        hotel = get_object_or_404(Hotel, pk=pk)
        
        # Create a placeholder scraping result
        result = ScrapingResult.objects.create(
            hotel=hotel,
            check_in=timezone.now().date(),
            check_out=timezone.now().date(),
            status='pending',
            method='manual'
        )
        
        messages.success(request, f'Scraping iniciado para {hotel.name}')
        return redirect('hotel_detail', pk=pk)


class SyncOTASyncView(LoginRequiredMixin, View):
    """Sync hotel with OTASync"""
    
    def post(self, request, pk):
        hotel = get_object_or_404(Hotel, pk=pk)
        
        if not hotel.otasync_enabled:
            messages.error(request, 'Este hotel no tiene OTASync habilitado.')
            return redirect('hotel_detail', pk=pk)
        
        messages.success(request, f'Sincronización con OTASync iniciada para {hotel.name}')
        return redirect('hotel_detail', pk=pk)


class ToggleHotelStatusView(LoginRequiredMixin, View):
    """Toggle hotel status"""
    
    def post(self, request, pk):
        hotel = get_object_or_404(Hotel, pk=pk)
        
        if hotel.status == 'active':
            hotel.status = 'inactive'
        else:
            hotel.status = 'active'
        
        hotel.save()
        messages.success(request, f'Estado de {hotel.name} cambiado a {hotel.get_status_display()}')
        return redirect('hotel_detail', pk=pk)


@method_decorator(csrf_exempt, name='dispatch')
class BulkScrapeView(LoginRequiredMixin, View):
    """
    🤖 SCRAPING MASIVO INTELIGENTE - SOLO DJANGO
    ===========================================
    
    Ejecuta el scraping masivo directamente desde Django:
    1. 🎯 20 fechas por hotel
    2. 📊 Aplicar márgenes
    3. 💾 Guardar en BD
    4. 🔄 Sincronizar OTASync
    5. ➡️ Continuar siguiente hotel
    """
    
    def post(self, request):
        try:
            print("⭐ BULK SCRAPE VIEW POST RECIBIDO")
            print(f"⭐ POST DATA: {request.POST}")
            print(f"⭐ Content-Type: {request.headers.get('Content-Type')}")
            
            # 🏨 OBTENER HOTELES SELECCIONADOS O TODOS
            selected_hotels = request.POST.getlist('hotels')
            print(f"⭐ HOTELES SELECCIONADOS: {selected_hotels}")
            
            if selected_hotels:
                # Scraping de hoteles específicos
                hotels_to_scrape = Hotel.objects.filter(id__in=selected_hotels)
                message = f'Iniciando scraping de {len(hotels_to_scrape)} hoteles seleccionados...'
                print(f"⭐ {message}")
            else:
                # Scraping de todos los hoteles activos
                hotels_to_scrape = Hotel.objects.filter(status='active')
                message = f'Iniciando scraping masivo de {len(hotels_to_scrape)} hoteles activos...'
                print(f"⭐ {message}")
            
            if not hotels_to_scrape.exists():
                error_message = 'No hay hoteles activos para scraping.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': error_message}, status=400)
                messages.error(request, error_message)
                return redirect('hotel_list')
            
            # 🚀 EJECUTAR SCRAPING INTELIGENTE
            print("⭐ Iniciando scraping inteligente")
            self.run_intelligent_scraping(hotels_to_scrape, request)
            print("⭐ Thread de scraping iniciado")
            
            # Para requests AJAX, devolver JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                print("⭐ Devolviendo respuesta JSON")
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'hotels_count': len(hotels_to_scrape)
                })
            
            # Para requests normales, redireccionar
            messages.info(request, message)
            return redirect('hotel_list')
            
        except Exception as e:
            error_message = f'Error iniciando scraping masivo: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_message}, status=500)
            messages.error(request, error_message)
            return redirect('hotel_list')
    
    def run_intelligent_scraping(self, hotels, request):
        """
        🤖 Ejecutar scraping inteligente para los hoteles especificados
        """
        import threading
        from intelligent_scraper import IntelligentScraper
        
        def scraping_worker():
            """Worker que ejecuta el scraping en background"""
            try:
                print("🔍 WORKER: Iniciando scraper inteligente")
                scraper = IntelligentScraper(headless=True)
                print("🔍 WORKER: Scraper iniciado correctamente")
                
                # Contador para progreso
                total_dates_obtained = 0
                total_hotels_processed = 0
                
                for i, hotel in enumerate(hotels, 1):
                    try:
                        print(f"🏨 [{i}/{len(hotels)}] Procesando: {hotel.name}")
                        
                        # 🎯 SCRAPING INTELIGENTE (20 fechas objetivo)
                        results = scraper.scrape_hotel_intelligent(
                            hotel_url=hotel.url,
                            hotel_id=hotel.id,
                            max_attempts=20
                        )
                        
                        dates_obtained = len(results)
                        total_dates_obtained += dates_obtained
                        total_hotels_processed += 1
                        
                        print(f"✅ {hotel.name}: {dates_obtained}/20 fechas obtenidas")
                        
                        # Actualizar timestamp del hotel
                        hotel.last_scraped = timezone.now()
                        hotel.save()
                        
                    except Exception as hotel_error:
                        print(f"❌ Error en {hotel.name}: {hotel_error}")
                        continue
                
                print(f"🎉 SCRAPING COMPLETADO: {total_dates_obtained} fechas de {total_hotels_processed} hoteles")
                
            except Exception as e:
                print(f"❌ Error general en scraping: {e}")
        
        # 🚀 EJECUTAR EN BACKGROUND THREAD
        thread = threading.Thread(target=scraping_worker, daemon=True)
        thread.start()
        
        messages.success(request, '🚀 Scraping inteligente iniciado en background. Los resultados aparecerán automáticamente.')


class IndividualScrapeView(LoginRequiredMixin, View):
    """
    🏨 SCRAPING INDIVIDUAL INTELIGENTE - SOLO DJANGO
    ===============================================
    Scraping de un solo hotel con 20 fechas objetivo
    """
    
    def post(self, request, pk):
        try:
            hotel = get_object_or_404(Hotel, pk=pk)
            
            # 🚀 EJECUTAR SCRAPING INTELIGENTE
            self.run_individual_scraping(hotel, request)
            
            messages.success(request, f'🚀 Scraping de {hotel.name} iniciado. Obteniendo 20 fechas...')
            return redirect('hotel_detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f'Error iniciando scraping: {str(e)}')
            return redirect('hotel_detail', pk=pk)
    
    def run_individual_scraping(self, hotel, request):
        """Ejecutar scraping individual en background"""
        import threading
        from intelligent_scraper import IntelligentScraper
        
        def scraping_worker():
            try:
                scraper = IntelligentScraper(headless=True)
                
                print(f"🏨 Iniciando scraping inteligente: {hotel.name}")
                
                # 🎯 SCRAPING INTELIGENTE (20 fechas objetivo)
                results = scraper.scrape_hotel_intelligent(
                    hotel_url=hotel.url,
                    hotel_id=hotel.id,
                    max_attempts=20
                )
                
                dates_obtained = len(results)
                print(f"✅ {hotel.name}: {dates_obtained}/20 fechas obtenidas")
                
                # Actualizar timestamp
                hotel.last_scraped = timezone.now()
                hotel.save()
                
            except Exception as e:
                print(f"❌ Error scraping {hotel.name}: {e}")
        
        # Ejecutar en background
        thread = threading.Thread(target=scraping_worker, daemon=True)
        thread.start()


class BulkSyncView(LoginRequiredMixin, View):
    """Bulk sync with OTASync"""
    
    def post(self, request):
        selected_hotels = request.POST.getlist('hotels')
        if not selected_hotels:
            messages.error(request, 'No se seleccionaron hoteles.')
            return redirect('hotel_list')
        
        count = len(selected_hotels)
        messages.success(request, f'Sincronización masiva con OTASync iniciada para {count} hoteles.')
        return redirect('hotel_list')


class BulkUpdateStatusView(LoginRequiredMixin, View):
    """Bulk update hotel status"""
    
    def post(self, request):
        selected_hotels = request.POST.getlist('hotels')
        new_status = request.POST.get('status')
        
        if not selected_hotels or not new_status:
            messages.error(request, 'Faltan parámetros para la actualización masiva.')
            return redirect('hotel_list')
        
        Hotel.objects.filter(id__in=selected_hotels).update(status=new_status)
        count = len(selected_hotels)
        messages.success(request, f'{count} hoteles actualizados a estado {new_status}.')
        return redirect('hotel_list')


class ScrapingResultListView(LoginRequiredMixin, ListView):
    """List scraping results for a hotel"""
    model = ScrapingResult
    template_name = 'hotels/scraping_results.html'
    context_object_name = 'results'
    paginate_by = 50
    
    def get_queryset(self):
        hotel_pk = self.kwargs.get('hotel_pk')
        return ScrapingResult.objects.filter(hotel_id=hotel_pk).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hotel'] = get_object_or_404(Hotel, pk=self.kwargs.get('hotel_pk'))
        return context


class ScrapingResultDetailView(LoginRequiredMixin, DetailView):
    """Scraping result detail"""
    model = ScrapingResult
    template_name = 'hotels/scraping_result_detail.html'
    context_object_name = 'result'


class ImportHotelsView(LoginRequiredMixin, View):
    """Import hotels from file"""
    
    def get(self, request):
        return render(request, 'hotels/import_hotels.html')
    
    def post(self, request):
        messages.info(request, 'Función de importación en desarrollo.')
        return redirect('hotel_list')


class ExportHotelsView(LoginRequiredMixin, View):
    """Export hotels to file"""
    
    def get(self, request):
        messages.info(request, 'Función de exportación en desarrollo.')
        return redirect('hotel_list')
