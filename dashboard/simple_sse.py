from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views import View
import json
import time
from .sse_helpers import SimpleSSEHandler

class SimpleSSEView(View):
    """Vista SSE simplificada para depuración"""
    
    def get(self, request):
        """Stream de eventos SSE"""
        # Usamos una implementación más robusta del helper
        def event_stream():
            """Generador de eventos"""
            # Inicio del stream
            yield "retry: 1000\n\n"
            yield "event: connected\ndata: {\"message\": \"Conexión establecida\"}\n\n"
            
            # Enviar eventos como prueba - versión simplificada
            for i in range(1, 6):  # Menos eventos para depuración
                # Formato SSE: event: tipo\ndata: {...}\n\n
                yield f"event: test\ndata: {{\"counter\": {i}, \"message\": \"Evento de prueba {i}\"}}\n\n"
                time.sleep(1)
            
            # Evento final
            yield "event: complete\ndata: {\"message\": \"Secuencia de prueba completada\"}\n\n"
        
        # Crear respuesta streaming con headers optimizados
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        
        # Headers para SSE más completos
        response['Cache-Control'] = 'no-cache, no-transform'
        # No usar 'Connection': 'keep-alive' (no permitido en WSGI)
        response['X-Accel-Buffering'] = 'no'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Credentials'] = 'true'
        
        return response

class TestWebhookView(View):
    """Vista webhook para pruebas"""
    
    def post(self, request):
        """Recibir evento por webhook"""
        try:
            data = json.loads(request.body.decode('utf-8'))
            # Simplemente devolver los datos recibidos
            return JsonResponse({
                "status": "success",
                "received_data": data,
                "message": "Evento recibido correctamente"
            })
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "error": str(e)
            }, status=400)
