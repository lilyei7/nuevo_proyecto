from django.http import HttpResponse, JsonResponse
import json
import time

class SimpleSSEHandler:
    """Manejador de eventos SSE simplificado"""
    
    @staticmethod
    def generate_events(num_events=10, delay=1):
        """Genera una secuencia de eventos SSE"""
        # Cabeceras iniciales
        yield "retry: 1000\n\n"
        yield "event: connected\ndata: {\"message\": \"Conexión establecida\"}\n\n"
        
        # Eventos de prueba
        for i in range(1, num_events + 1):
            yield f"event: test\ndata: {{\"counter\": {i}, \"message\": \"Evento de prueba {i}\"}}\n\n"
            time.sleep(delay)
        
        # Evento final
        yield "event: complete\ndata: {\"message\": \"Secuencia de prueba completada\"}\n\n"
    
    @staticmethod
    def create_sse_response(generator):
        """Crea una respuesta HTTP con formato SSE"""
        response = HttpResponse(
            generator,
            content_type="text/event-stream"
        )
        
        # Headers críticos para SSE
        response["Cache-Control"] = "no-cache, no-transform"
        response["Connection"] = "keep-alive"
        response["X-Accel-Buffering"] = "no"
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Credentials"] = "true"
        
        return response

def simple_sse_view(request):
    """Vista simple para SSE que no requiere clase"""
    generator = SimpleSSEHandler.generate_events(num_events=5, delay=1)
    return SimpleSSEHandler.create_sse_response(generator)
