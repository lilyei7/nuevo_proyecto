import json
import time
import threading
import queue
from datetime import datetime
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)

class ScrapingEventManager:
    """Gestor de eventos de scraping en tiempo real"""
    
    def __init__(self):
        self.clients = set()
        self.event_queue = queue.Queue()
        self.lock = threading.Lock()
        
    def add_client(self, client_queue):
        """Agregar un cliente SSE"""
        with self.lock:
            self.clients.add(client_queue)
            logger.info(f"📡 Cliente SSE agregado. Total: {len(self.clients)}")
    
    def remove_client(self, client_queue):
        """Remover un cliente SSE"""
        with self.lock:
            self.clients.discard(client_queue)
            logger.info(f"📡 Cliente SSE removido. Total: {len(self.clients)}")
    
    def broadcast_event(self, event_type, data):
        """Enviar evento a todos los clientes conectados"""
        event_data = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        with self.lock:
            clients_to_remove = set()
            for client_queue in self.clients.copy():
                try:
                    client_queue.put_nowait(event_data)
                except queue.Full:
                    # Cliente desconectado o cola llena
                    clients_to_remove.add(client_queue)
            
            # Remover clientes desconectados
            for client in clients_to_remove:
                self.clients.discard(client)
        
        logger.info(f"📡 Evento '{event_type}' enviado a {len(self.clients)} clientes")

# Instancia global del gestor de eventos
event_manager = ScrapingEventManager()

@method_decorator(csrf_exempt, name='dispatch')
class RealtimeEventsView(View):  # Sin LoginRequiredMixin para permitir conexiones anónimas
    """Vista de Server-Sent Events para monitor en tiempo real"""
    
    def get(self, request):
        """Stream de eventos SSE - Versión ultra simplificada para resolver error 500"""
        logger.info("⭐ Conexión SSE recibida desde %s", request.META.get('REMOTE_ADDR', 'Unknown'))
        
        # Usamos el helper que ya sabemos que funciona
        def event_stream():
            """Generador de eventos de prueba"""
            try:
                # Headers iniciales
                yield "retry: 1000\n\n"
                
                # Conexión establecida
                logger.info("📤 Enviando evento de conexión inicial")
                yield f"event: connected\ndata: {{\"message\": \"Conexión establecida\", \"timestamp\": \"{datetime.now().isoformat()}\"}}\n\n"
                
                # Ping para mantener viva la conexión
                yield ": ping\n\n"
                
                # Estado inicial (datos de demostración)
                yield f"event: status\ndata: {{\"total_scrapes\": 150, \"today_scrapes\": 25, \"avg_price\": 120.50, \"status\": \"active\", \"timestamp\": \"{datetime.now().isoformat()}\"}}\n\n"
                
                # Eventos de prueba - simplificados para evitar errores
                for i in range(1, 6):
                    # Eventos de heartbeat cada 2 segundos
                    yield f"event: heartbeat\ndata: {{\"counter\": {i}, \"timestamp\": \"{datetime.now().isoformat()}\"}}\n\n"
                    
                    # Eventos simulados de scraping
                    if i % 2 == 0:
                        yield f"event: scraping_progress\ndata: {{\"hotel_id\": {9350+i}, \"progress\": {i*20}, \"message\": \"Simulación de progreso {i*20}%\", \"timestamp\": \"{datetime.now().isoformat()}\"}}\n\n"
                    
                    time.sleep(2)
                
                logger.info("✅ Secuencia de eventos SSE completada")
            
            except Exception as e:
                logger.error(f"❌ Error en stream SSE: {str(e)}")
                yield f"event: error\ndata: {{\"message\": \"Error en servidor\", \"error\": \"{str(e)}\"}}\n\n"
        
        # Crear respuesta streaming para eventos SSE
        logger.info("🔄 Creando respuesta StreamingHttpResponse")
        response = HttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        
        # Headers esenciales para SSE - versión completa y detallada
        response['Cache-Control'] = 'no-cache, no-transform'
        response['Connection'] = 'keep-alive'
        response['X-Accel-Buffering'] = 'no'  
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Credentials'] = 'true'
        
        return response
    
    def format_sse_event(self, event_type, data):
        """Formatear evento SSE"""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    def get_scraping_status(self):
        """Obtener estado actual del scraping"""
        # Versión simplificada que no depende de la base de datos
        return {
            'total_scrapes': 150,
            'today_scrapes': 25,
            'avg_price': 120.50,
            'status': 'active',
            'last_update': datetime.now().isoformat()
        }

@method_decorator(csrf_exempt, name='dispatch')
class ScrapingEventWebhookView(View):
    """API Webhook para recibir eventos de scraping"""
    
    def post(self, request):
        """Recibir evento de scraping desde webhook"""
        try:
            data = json.loads(request.body.decode('utf-8'))
            
            # Validar datos básicos
            if 'type' not in data or 'data' not in data:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Formato de evento inválido'
                }, status=400)
            
            # Broadcast del evento recibido
            event_manager.broadcast_event(data['type'], data['data'])
            
            return JsonResponse({
                'status': 'success',
                'message': f'Evento {data["type"]} procesado correctamente'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'JSON inválido'
            }, status=400)
            
        except Exception as e:
            logger.error(f"❌ Error en webhook: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error al procesar webhook: {str(e)}'
            }, status=500)
