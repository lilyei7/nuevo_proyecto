"""
Vista SSE minimalista para diagnóstico de error 500
"""

from django.http import StreamingHttpResponse
from django.views import View
import time
from datetime import datetime

class MiniSSEView(View):
    """Vista SSE mínima para diagnóstico"""
    
    def get(self, request):
        """Stream SSE ultra simplificado"""
        
        def event_stream():
            # Configuración inicial
            yield "retry: 1000\n\n"
            yield "event: connected\ndata: {\"message\": \"Conexión establecida\"}\n\n"
            
            # Enviar solo un evento para simplificar
            yield f"event: test\ndata: {{\"timestamp\": \"{datetime.now().isoformat()}\"}}\n\n"
            time.sleep(1)
            
            # Evento final
            yield "event: complete\ndata: {\"message\": \"Prueba completada\"}\n\n"
        
        # Crear respuesta con headers mínimos
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        
        # Solo headers esenciales
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        
        return response
