
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import threading
from .models import Hotel
from intelligent_scraper import IntelligentScraper

@method_decorator(csrf_exempt, name='dispatch')
class BulkScrapeAPIView(View):
    """
    API para el scraping masivo inteligente de hoteles
    """
    
    def post(self, request):
        try:
            print("🚀 API: Iniciando scraping masivo")
            
            # 🏨 OBTENER HOTELES ACTIVOS
            hotels_to_scrape = Hotel.objects.filter(status='active')
            
            if not hotels_to_scrape.exists():
                return JsonResponse({'error': 'No hay hoteles activos para scraping.'}, status=400)
            
            # 🚀 EJECUTAR SCRAPING INTELIGENTE
            self._run_intelligent_scraping(hotels_to_scrape)
            
            return JsonResponse({
                'success': True,
                'message': f'Iniciando scraping masivo de {len(hotels_to_scrape)} hoteles activos...',
                'hotels_count': len(hotels_to_scrape)
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error iniciando scraping masivo: {str(e)}'}, status=500)
    
    def _run_intelligent_scraping(self, hotels):
        """
        🤖 Ejecutar scraping inteligente para los hoteles especificados
        """
        def scraping_worker():
            try:
                print("🔍 API WORKER: Iniciando scraper inteligente")
                scraper = IntelligentScraper(headless=True)
                print("🔍 API WORKER: Scraper iniciado correctamente")
                
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
                
                print(f"🎉 API SCRAPING COMPLETADO: {total_dates_obtained} fechas de {total_hotels_processed} hoteles")
                
            except Exception as e:
                print(f"❌ API Error general en scraping: {e}")
        
        # 🚀 EJECUTAR EN BACKGROUND THREAD
        thread = threading.Thread(target=scraping_worker, daemon=True)
        thread.start()


@method_decorator(csrf_exempt, name='dispatch')
class HotelListAPIView(View):
    """API para listar hoteles"""
    def get(self, request):
        hotels = Hotel.objects.all()
        data = [{'id': h.id, 'name': h.name, 'url': h.url, 'status': h.status} for h in hotels]
        return JsonResponse({'hotels': data})


@method_decorator(csrf_exempt, name='dispatch')
class HotelDetailAPIView(View):
    """API para detalles de un hotel específico"""
    def get(self, request, pk):
        try:
            hotel = Hotel.objects.get(pk=pk)
            data = {
                'id': hotel.id,
                'name': hotel.name,
                'url': hotel.url,
                'status': hotel.status,
                'otasync_id': hotel.otasync_id,
                'last_scraped': hotel.last_scraped.isoformat() if hotel.last_scraped else None
            }
            return JsonResponse(data)
        except Hotel.DoesNotExist:
            return JsonResponse({'error': 'Hotel no encontrado'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class ScrapeHotelAPIView(View):
    """API para scraping de un hotel específico"""
    def post(self, request, pk):
        try:
            hotel = Hotel.objects.get(pk=pk)
            
            # Lanzar scraping en thread
            threading.Thread(
                target=self._scrape_hotel,
                args=(hotel,),
                daemon=True
            ).start()
            
            return JsonResponse({
                'success': True,
                'message': f'Iniciado scraping para {hotel.name}'
            })
        except Hotel.DoesNotExist:
            return JsonResponse({'error': 'Hotel no encontrado'}, status=404)
    
    def _scrape_hotel(self, hotel):
        try:
            scraper = IntelligentScraper(headless=True)
            results = scraper.scrape_hotel_intelligent(
                hotel_url=hotel.url,
                hotel_id=hotel.id,
                max_attempts=20
            )
            print(f"✅ API: {hotel.name}: {len(results)}/20 fechas obtenidas")
            
            # Actualizar timestamp
            hotel.last_scraped = timezone.now()
            hotel.save()
        except Exception as e:
            print(f"❌ API Error scraping {hotel.name}: {e}")


@method_decorator(csrf_exempt, name='dispatch')
class SyncOTASyncAPIView(View):
    """API para sincronizar un hotel con OTASync"""
    def post(self, request, pk):
        try:
            hotel = Hotel.objects.get(pk=pk)
            # Implementar lógica de sincronización
            return JsonResponse({
                'success': True,
                'message': f'Sincronización iniciada para {hotel.name}'
            })
        except Hotel.DoesNotExist:
            return JsonResponse({'error': 'Hotel no encontrado'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class BulkSyncAPIView(View):
    """API para sincronizar todos los hoteles activos con OTASync"""
    def post(self, request):
        try:
            # 🏨 OBTENER HOTELES ACTIVOS
            hotels_to_sync = Hotel.objects.filter(status='active')
            
            if not hotels_to_sync.exists():
                return JsonResponse({'error': 'No hay hoteles activos para sincronizar.'}, status=400)
            
            # 🚀 EJECUTAR SINCRONIZACIÓN EN BACKGROUND
            self._run_sync_thread(hotels_to_sync)
            
            return JsonResponse({
                'success': True,
                'message': f'Iniciando sincronización de {len(hotels_to_sync)} hoteles activos...',
                'hotels_count': len(hotels_to_sync)
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error iniciando sincronización masiva: {str(e)}'}, status=500)
    
    def _run_sync_thread(self, hotels):
        def sync_worker():
            from otasync_integration import OTASyncClient
            
            try:
                print("🔄 API SYNC WORKER: Iniciando sincronización")
                client = OTASyncClient()
                total_synced = 0
                
                for i, hotel in enumerate(hotels, 1):
                    try:
                        if not hotel.otasync_id:
                            print(f"⚠️ Hotel {hotel.name} no tiene ID de OTASync")
                            continue
                        
                        print(f"🏨 [{i}/{len(hotels)}] Sincronizando: {hotel.name}")
                        success = client.sync_prices_for_property(hotel.otasync_id)
                        
                        if success:
                            total_synced += 1
                            print(f"✅ {hotel.name}: Precios sincronizados correctamente")
                        else:
                            print(f"❌ {hotel.name}: Error en sincronización")
                            
                    except Exception as hotel_error:
                        print(f"❌ Error sincronizando {hotel.name}: {hotel_error}")
                        continue
                
                print(f"🎉 API SYNC COMPLETADA: {total_synced}/{len(hotels)} hoteles sincronizados")
                
            except Exception as e:
                print(f"❌ API Error general en sincronización: {e}")
        
        thread = threading.Thread(target=sync_worker, daemon=True)
        thread.start()


class ScrapingResultListAPIView(View):
    """API para listar resultados de scraping para un hotel"""
    def get(self, request, pk):
        # Implementar lógica para obtener resultados
        return JsonResponse({
            'success': True, 
            'results': [
                # Aquí irían los resultados
            ]
        })
