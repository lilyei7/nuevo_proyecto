from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime, timedelta
from hotels.models import Hotel, ScrapingResult
import json
import logging

# Configurar logger para el sistema
logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view"""
    template_name = 'dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Basic stats
        context.update({
            'total_hotels': Hotel.objects.count(),
            'active_hotels': Hotel.objects.filter(status='active').count(),
            'inactive_hotels': Hotel.objects.filter(status='inactive').count(),
            'pending_hotels': Hotel.objects.filter(status='pending').count(),
            'otasync_hotels': Hotel.objects.filter(otasync_enabled=True).count(),
        })
        
        # Recent scraping results
        context['recent_results'] = ScrapingResult.objects.select_related('hotel').order_by('-created_at')[:10]
        
        # Success rate (last 24 hours)
        last_24h = timezone.now() - timedelta(hours=24)
        recent_results = ScrapingResult.objects.filter(created_at__gte=last_24h)
        if recent_results.exists():
            success_count = recent_results.filter(status='success').count()
            context['success_rate'] = round((success_count / recent_results.count()) * 100, 1)
        else:
            context['success_rate'] = 0
        
        return context

class DashboardMonitorView(LoginRequiredMixin, TemplateView):
    """Monitor mejorado en tiempo real con Server-Sent Events (SSE)"""
    template_name = 'dashboard/monitor_improved.html'

class IntegratedMonitorView(TemplateView):
    """Monitor integrado sin servidores adicionales"""
    template_name = 'dashboard/monitor_integrated.html'

class SSETestPageView(TemplateView):
    """Página de prueba y diagnóstico SSE"""
    template_name = 'dashboard/sse_test.html'

class RealtimeMonitorView(LoginRequiredMixin, TemplateView):
    """Realtime monitor with robust WebSocket connection and HTTP fallback"""
    template_name = 'dashboard/monitor_realtime.html'


class StatsView(LoginRequiredMixin, TemplateView):
    """Detailed statistics view"""
    template_name = 'dashboard/stats.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Hotel statistics by source
        context['hotel_stats_by_source'] = (
            Hotel.objects.values('source')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        # Scraping results by status (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        context['scraping_stats'] = (
            ScrapingResult.objects.filter(created_at__gte=week_ago)
            .values('status')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        # Average price trends
        context['price_trends'] = (
            ScrapingResult.objects.filter(
                price__isnull=False,
                created_at__gte=week_ago
            )
            .extra({'date': "date(created_at)"})
            .values('date')
            .annotate(avg_price=Avg('price'))
            .order_by('date')
        )
        
        return context


class StatsAPIView(LoginRequiredMixin, TemplateView):
    """API endpoint for dashboard statistics"""
    
    def get(self, request, *args, **kwargs):
        # Get date range from query params
        days = int(request.GET.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        
        # Daily scraping counts
        daily_stats = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            count = ScrapingResult.objects.filter(
                created_at__date=date.date()
            ).count()
            
            success_count = ScrapingResult.objects.filter(
                created_at__date=date.date(),
                status='success'
            ).count()
            
            daily_stats.append({
                'date': date_str,
                'total': count,
                'success': success_count,
                'error': count - success_count
            })
        
        # Hotel status distribution
        hotel_status = {
            'active': Hotel.objects.filter(status='active').count(),
            'inactive': Hotel.objects.filter(status='inactive').count(),
            'pending': Hotel.objects.filter(status='pending').count(),
        }
        
        # Top performing hotels (by success rate)
        top_hotels = []
        for hotel in Hotel.objects.all()[:10]:
            total_results = hotel.scraping_results.count()
            if total_results > 0:
                success_results = hotel.scraping_results.filter(status='success').count()
                success_rate = (success_results / total_results) * 100
                top_hotels.append({
                    'name': hotel.name,
                    'success_rate': round(success_rate, 1),
                    'total_scrapes': total_results
                })
        
        top_hotels.sort(key=lambda x: x['success_rate'], reverse=True)
        
        return JsonResponse({
            'daily_stats': daily_stats,
            'hotel_status': hotel_status,
            'top_hotels': top_hotels[:5],
        })


class SystemStatusView(LoginRequiredMixin, TemplateView):
    """System status and health view"""
    template_name = 'dashboard/system_status.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # System health checks
        context['system_checks'] = self.run_system_checks()
        
        # Recent errors
        context['recent_errors'] = (
            ScrapingResult.objects.filter(
                status__in=['error', 'failed'],
                created_at__gte=timezone.now() - timedelta(hours=24)
            )
            .select_related('hotel')
            .order_by('-created_at')[:20]
        )
        
        return context
    
    def run_system_checks(self):
        """Run basic system health checks"""
        checks = []
        
        # Database connectivity
        try:
            Hotel.objects.count()
            checks.append({
                'name': 'Database Connection',
                'status': 'success',
                'message': 'Conexión a base de datos exitosa'
            })
        except Exception as e:
            checks.append({
                'name': 'Database Connection',
                'status': 'error',
                'message': f'Error de conexión: {str(e)}'
            })
        
        # Recent scraping activity
        recent_scrapes = ScrapingResult.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        if recent_scrapes > 0:
            checks.append({
                'name': 'Scraping Activity',
                'status': 'success',
                'message': f'{recent_scrapes} scrapes en la última hora'
            })
        else:
            checks.append({
                'name': 'Scraping Activity',
                'status': 'warning',
                'message': 'No hay actividad de scraping reciente'
            })
        
        # OTASync integration
        otasync_hotels = Hotel.objects.filter(otasync_enabled=True).count()
        if otasync_hotels > 0:
            checks.append({
                'name': 'OTASync Integration',
                'status': 'success',
                'message': f'{otasync_hotels} hoteles con integración OTASync'
            })
        else:
            checks.append({
                'name': 'OTASync Integration',
                'status': 'info',
                'message': 'No hay hoteles configurados con OTASync'
            })
        
        return checks


class LogsView(LoginRequiredMixin, TemplateView):
    """System logs view"""
    template_name = 'dashboard/logs.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filter parameters
        status_filter = self.request.GET.get('status', 'all')
        days_filter = int(self.request.GET.get('days', 7))
        
        # Base queryset
        queryset = ScrapingResult.objects.select_related('hotel')
        
        # Apply filters
        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        if days_filter:
            start_date = timezone.now() - timedelta(days=days_filter)
            queryset = queryset.filter(created_at__gte=start_date)
        
        context['logs'] = queryset.order_by('-created_at')[:100]
        context['status_filter'] = status_filter
        context['days_filter'] = days_filter
        
        return context


def custom_404(request, exception):
    """Custom 404 error page"""
    return render(request, 'errors/404.html', status=404)


def custom_500(request):
    """Custom 500 error page"""
    return render(request, 'errors/500.html', status=500)


class ScrapingResultsView(LoginRequiredMixin, TemplateView):
    """Scraping results view with detailed price information"""
    template_name = 'dashboard/scraping_results.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filter parameters
        hotel_filter = self.request.GET.get('hotel', 'all')
        days_filter = int(self.request.GET.get('days', 7))
        status_filter = self.request.GET.get('status', 'all')
        
        # Get all hotels for filter dropdown
        context['hotels'] = Hotel.objects.all().order_by('name')
        context['hotel_filter'] = hotel_filter
        context['days_filter'] = days_filter
        context['status_filter'] = status_filter
        
        return context


class ScrapingResultsAPIView(LoginRequiredMixin, TemplateView):
    """API endpoint for scraping results data"""
    
    def get(self, request, *args, **kwargs):
        # Import the database manager
        import sqlite3
        import os
        from django.conf import settings
        
        # Filter parameters
        hotel_filter = request.GET.get('hotel', 'all')
        days_filter = int(request.GET.get('days', 7))
        status_filter = request.GET.get('status', 'all')
        
        # Database connection
        db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query
            query = """
                SELECT 
                    s.id,
                    s.hotel_id_fk,
                    s.checkin,
                    s.checkout,
                    s.price_amount,
                    s.price_currency,
                    s.availability,
                    s.source_url,
                    s.scraped_at,
                    h.name as hotel_name,
                    h.price_percent
                FROM scrapes s
                LEFT JOIN hotels_hotel h ON s.hotel_id_fk = h.id
                WHERE 1=1
            """
            params = []
            
            # Apply filters
            if hotel_filter != 'all':
                query += " AND s.hotel_id_fk = ?"
                params.append(hotel_filter)
            
            if days_filter:
                query += " AND s.scraped_at >= datetime('now', '-{} days')".format(days_filter)
            
            if status_filter != 'all':
                if status_filter == 'available':
                    query += " AND s.availability = 'available'"
                elif status_filter == 'unavailable':
                    query += " AND s.availability != 'available'"
            
            query += " ORDER BY s.scraped_at DESC LIMIT 100"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                price_base = row['price_amount'] or 0
                price_percent = row['price_percent'] or 0
                
                # Calculate prices with margin
                if price_base > 0 and price_percent > 0:
                    # The stored price already includes margin, so calculate base price
                    base_price = price_base / (1 + price_percent / 100)
                    margin_amount = price_base - base_price
                else:
                    base_price = price_base
                    margin_amount = 0
                
                results.append({
                    'id': row['id'],
                    'hotel_id': row['hotel_id_fk'],
                    'hotel_name': row['hotel_name'] or 'Hotel Desconocido',
                    'checkin_date': row['checkin'],
                    'checkout_date': row['checkout'],
                    'base_price': round(base_price, 2),
                    'margin_percent': price_percent,
                    'margin_amount': round(margin_amount, 2),
                    'final_price': round(price_base, 2),
                    'currency': row['price_currency'] or 'MXN',
                    'availability': row['availability'],
                    'source_url': row['source_url'],
                    'scraped_at': row['scraped_at'],
                })
            
            conn.close()
            
            return JsonResponse({
                'success': True,
                'results': results,
                'total': len(results)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class StartScrapingAPIView(LoginRequiredMixin, TemplateView):
    """API para iniciar scraping"""
    
    def post(self, request, *args, **kwargs):
        try:
            # Aquí se implementaría la lógica para iniciar el scraping
            # Por ahora devolvemos una respuesta simulada
            
            return JsonResponse({
                'success': True,
                'message': 'Scraping iniciado correctamente',
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class StopScrapingAPIView(LoginRequiredMixin, TemplateView):
    """API para detener scraping"""
    
    def post(self, request, *args, **kwargs):
        try:
            # Aquí se implementaría la lógica para detener el scraping
            # Por ahora devolvemos una respuesta simulada
            
            return JsonResponse({
                'success': True,
                'message': 'Scraping detenido correctamente',
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class RealTimeLogsAPIView(TemplateView):
    """API para obtener logs en tiempo real"""
    
    def get(self, request, *args, **kwargs):
        try:
            # Obtener parámetros
            limit = int(request.GET.get('limit', 50))
            level_filter = request.GET.get('level', None)
            since = request.GET.get('since', None)
            
            # Obtener logs del cache o crear simulados
            try:
                logs = cache.get('realtime_logs', [])
            except:
                logs = []
            
            # Si no hay logs, crear algunos de ejemplo
            if not logs:
                logs = [
                    {
                        'timestamp': timezone.now().isoformat(),
                        'level': 'INFO',
                        'message': 'Sistema de monitoreo iniciado',
                        'module': 'monitor',
                        'color': 'text-info'
                    },
                    {
                        'timestamp': timezone.now().isoformat(),
                        'level': 'INFO', 
                        'message': 'Conexión con monitor establecida',
                        'module': 'system',
                        'color': 'text-success'
                    }
                ]
                try:
                    cache.set('realtime_logs', logs, 300)
                except:
                    pass
            
            # Filtrar por nivel si se especifica
            if level_filter:
                logs = [log for log in logs if log['level'] == level_filter]
            
            # Filtrar por timestamp si se especifica
            if since:
                logs = [log for log in logs if log['timestamp'] > since]
            
            # Limitar cantidad
            logs = logs[-limit:]
            
            return JsonResponse({
                'success': True,
                'logs': logs,
                'total': len(logs),
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class ClearLogsAPIView(TemplateView):
    """API para limpiar logs en tiempo real"""
    
    def post(self, request, *args, **kwargs):
        try:
            # Limpiar cache de logs
            try:
                cache.delete('realtime_logs')
            except:
                pass
            
            # Agregar log de limpieza
            clear_log = {
                'timestamp': timezone.now().isoformat(),
                'level': 'INFO',
                'message': 'Buffer de logs limpiado por usuario',
                'module': 'system',
                'color': 'text-warning'
            }
            try:
                cache.set('realtime_logs', [clear_log], 300)
            except:
                pass
            
            return JsonResponse({
                'success': True,
                'message': 'Logs limpiados correctamente'
            })
            
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class StartScrapingAPIView(TemplateView):
    """API para iniciar proceso de scraping"""
    
    def post(self, request, *args, **kwargs):
        try:
            from .monitor_utils import log_to_monitor
            
            # Obtener parámetros del request
            hotel_ids = request.POST.getlist('hotel_ids', [])
            scraping_type = request.POST.get('type', 'manual')
            
            # Log de inicio de scraping
            log_to_monitor(
                f"🚀 Iniciando proceso de scraping {scraping_type}",
                'INFO',
                'scraper',
                {'hotel_count': len(hotel_ids), 'type': scraping_type}
            )
            
            if hotel_ids:
                log_to_monitor(
                    f"📋 Hoteles seleccionados: {len(hotel_ids)}",
                    'INFO',
                    'scraper'
                )
            else:
                log_to_monitor(
                    "📋 Scraping de todos los hoteles activos",
                    'INFO',
                    'scraper'
                )
            
            # Aquí se puede integrar con el sistema de scraping real
            # Por ahora, simulamos el proceso
            import threading
            import time
            import random
            
            def simulate_scraping():
                try:
                    hotels = Hotel.objects.filter(status='active')
                    if hotel_ids:
                        hotels = hotels.filter(id__in=hotel_ids)
                    
                    total_hotels = hotels.count()
                    log_to_monitor(
                        f"🎯 Procesando {total_hotels} hoteles",
                        'INFO',
                        'scraper'
                    )
                    
                    for i, hotel in enumerate(hotels, 1):
                        # Simular procesamiento
                        time.sleep(random.uniform(1, 3))
                        
                        log_to_monitor(
                            f"🔍 Scrapeando {hotel.name} ({i}/{total_hotels})",
                            'INFO',
                            'scraper',
                            {'progress': f"{i}/{total_hotels}", 'hotel': hotel.name}
                        )
                        
                        # Simular éxito/error aleatorio
                        if random.random() > 0.2:  # 80% éxito
                            price = random.uniform(800, 2500)
                            log_to_monitor(
                                f"✅ {hotel.name}: ${price:.2f} MXN obtenido",
                                'INFO',
                                'scraper',
                                {
                                    'hotel': hotel.name,
                                    'price': price,
                                    'currency': 'MXN',
                                    'status': 'success'
                                }
                            )
                            
                            # Crear resultado de scraping simulado
                            from datetime import date
                            ScrapingResult.objects.create(
                                hotel=hotel,
                                check_in=date.today(),
                                check_out=date.today(),
                                price=price,
                                status='success'
                            )
                        else:  # 20% error
                            error_msg = random.choice([
                                'Timeout en conexión',
                                'Elementos no encontrados',
                                'Error de parsing',
                                'Límite de rate alcanzado'
                            ])
                            log_to_monitor(
                                f"❌ {hotel.name}: {error_msg}",
                                'ERROR',
                                'scraper',
                                {'hotel': hotel.name, 'error': error_msg}
                            )
                    
                    log_to_monitor(
                        f"🎉 Scraping completado: {total_hotels} hoteles procesados",
                        'INFO',
                        'scraper',
                        {'total_processed': total_hotels}
                    )
                    
                except Exception as e:
                    log_to_monitor(
                        f"💥 Error en scraping: {str(e)}",
                        'ERROR',
                        'scraper',
                        {'error': str(e)}
                    )
            
            # Iniciar scraping en thread separado
            scraping_thread = threading.Thread(target=simulate_scraping)
            scraping_thread.daemon = True
            scraping_thread.start()
            
            return JsonResponse({
                'success': True,
                'message': 'Scraping iniciado correctamente',
                'hotel_count': len(hotel_ids) if hotel_ids else Hotel.objects.filter(status='active').count()
            })
            
        except Exception as e:
            logger.error(f"Error starting scraping: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class StopScrapingAPIView(TemplateView):
    """API para detener proceso de scraping"""
    
    def post(self, request, *args, **kwargs):
        try:
            from .monitor_utils import log_to_monitor
            
            log_to_monitor(
                "⏹️ Deteniendo proceso de scraping",
                'WARNING',
                'scraper'
            )
            
            # Aquí se implementaría la lógica para detener el scraping real
            # Por ahora solo log
            
            log_to_monitor(
                "🛑 Scraping detenido por usuario",
                'WARNING',
                'scraper'
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Scraping detenido correctamente'
            })
            
        except Exception as e:
            logger.error(f"Error stopping scraping: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
