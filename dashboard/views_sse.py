from django.views.generic import TemplateView

class SSETestView(TemplateView):
    """Vista para probar conexiones SSE"""
    template_name = "sse_test.html"
