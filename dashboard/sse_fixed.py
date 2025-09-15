#!/usr/bin/env python3
"""
🔧 SSE CORREGIDO Y MEJORADO
===========================

Implementación corregida del Server-Sent Events que funciona
correctamente con Django y elimina los errores de conexión.
"""

from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from django.utils import timezone
from django.core.cache import cache
import json
import time
import logging

logger = logging.getLogger(__name__)

class FixedSSEView(View):
    """Vista SSE corregida que elimina errores de conexión"""
    
    def get(self, request):
        """Stream SSE mejorado y estable"""
        
        def generate_sse_events():
            """Generador de eventos SSE con manejo robusto de errores"""
            
            try:
                # Configuración inicial del stream
                yield "retry: 3000\n\n"
                yield f"event: connection\ndata: {{\"status\": \"connected\", \"timestamp\": \"{timezone.now().isoformat()}\"}}\n\n"
                
                # Contador de eventos
                event_count = 0
                
                while True:
                    try:
                        # Obtener stats del sistema
                        stats = self.get_system_stats()
                        
                        # Crear evento de datos
                        event_data = {
                            "event_id": event_count,
                            "timestamp": timezone.now().isoformat(),
                            "stats": stats,
                            "status": "active"
                        }
                        
                        yield f"event: stats\ndata: {json.dumps(event_data)}\n\n"
                        
                        event_count += 1
                        
                        # Verificar logs recientes
                        recent_logs = self.get_recent_logs()
                        if recent_logs:
                            log_event = {
                                "event_id": event_count,
                                "timestamp": timezone.now().isoformat(),
                                "logs": recent_logs
                            }
                            yield f"event: logs\ndata: {json.dumps(log_event)}\n\n"
                            event_count += 1
                        
                        # Heartbeat cada 5 segundos
                        time.sleep(5)
                        
                    except Exception as e:
                        logger.error(f"Error en SSE event generation: {e}")
                        # Enviar evento de error pero continuar
                        error_event = {
                            "error": str(e),
                            "timestamp": timezone.now().isoformat()
                        }
                        yield f"event: error\ndata: {json.dumps(error_event)}\n\n"
                        time.sleep(3)
                        
            except Exception as e:
                logger.error(f"Error crítico en SSE: {e}")
                # Enviar evento de desconexión
                yield f"event: disconnect\ndata: {{\"error\": \"{str(e)}\"}}\n\n"
    
        # Crear respuesta streaming con headers corregidos
        response = StreamingHttpResponse(
            generate_sse_events(),
            content_type='text/event-stream; charset=utf-8'
        )
        
        # Headers específicos para SSE funcionando
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['X-Accel-Buffering'] = 'no'  # Para nginx
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Headers'] = 'Cache-Control'
        
        return response
    
    def get_system_stats(self):
        """Obtener estadísticas del sistema"""
        try:
            # Stats básicas simuladas - puedes conectar con tu sistema real
            return {
                "active_connections": 1,
                "total_logs": cache.get('total_logs', 0),
                "error_count": cache.get('error_count', 0),
                "success_rate": 95.5,
                "last_update": timezone.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {
                "error": "Could not fetch stats",
                "timestamp": timezone.now().isoformat()
            }
    
    def get_recent_logs(self):
        """Obtener logs recientes"""
        try:
            # Obtener logs del cache si existen
            logs = cache.get('realtime_logs', [])
            # Devolver solo los más recientes
            return logs[-5:] if logs else []
        except Exception as e:
            logger.error(f"Error getting recent logs: {e}")
            return []


class SimpleHealthCheckView(View):
    """Vista simple para verificar que el sistema funciona"""
    
    def get(self, request):
        """Health check endpoint"""
        return JsonResponse({
            "status": "healthy",
            "timestamp": timezone.now().isoformat(),
            "message": "Sistema funcionando correctamente"
        })


class SSETestView(View):
    """Vista de prueba SSE más simple"""
    
    def get(self, request):
        """SSE de prueba super simple"""
        
        def simple_events():
            """Eventos de prueba simples"""
            yield "retry: 2000\n\n"
            
            for i in range(3):
                event_data = {
                    "counter": i + 1,
                    "message": f"Evento de prueba {i + 1}",
                    "timestamp": timezone.now().isoformat()
                }
                yield f"data: {json.dumps(event_data)}\n\n"
                time.sleep(2)
            
            # Evento final
            yield f"data: {{\"message\": \"Test completado\", \"final\": true}}\n\n"
        
        response = StreamingHttpResponse(
            simple_events(),
            content_type='text/event-stream'
        )
        
        response['Cache-Control'] = 'no-cache'
        response['Access-Control-Allow-Origin'] = '*'
        
        return response
