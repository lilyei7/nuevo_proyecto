#!/usr/bin/env python3
"""
📡 LOGGER EN TIEMPO REAL INTEGRADO
==================================

Sistema de logging que se integra directamente con Django
sin necesidad de servidores adicionales. Usa WebSockets
para transmisión en tiempo real.

Funcionalidades:
• Logs en tiempo real via WebSocket
• Buffer circular para historial
• Filtrado por nivel de log
• Integración directa con scraping
• Sin dependencias externas
"""

import json
import logging
import threading
import time
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional
from django.http import JsonResponse
from django.core.cache import cache

class RealTimeLogger:
    """
    📡 LOGGER EN TIEMPO REAL PARA DJANGO
    ===================================
    """
    
    def __init__(self, max_logs=1000):
        self.max_logs = max_logs
        self.logs_buffer = deque(maxlen=max_logs)
        self.active_connections = set()
        self.lock = threading.Lock()
        
        # Configurar handler personalizado
        self.setup_logging_handler()
    
    def setup_logging_handler(self):
        """Configurar handler para capturar logs"""
        
        class RealTimeHandler(logging.Handler):
            def __init__(self, logger_instance):
                super().__init__()
                self.logger_instance = logger_instance
                
            def emit(self, record):
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'level': record.levelname,
                    'message': record.getMessage(),
                    'module': record.module,
                    'line': record.lineno,
                    'color': self.get_level_color(record.levelname)
                }
                self.logger_instance.add_log(log_entry)
            
            def get_level_color(self, level):
                colors = {
                    'DEBUG': 'text-muted',
                    'INFO': 'text-info', 
                    'WARNING': 'text-warning',
                    'ERROR': 'text-danger',
                    'CRITICAL': 'text-danger'
                }
                return colors.get(level, 'text-secondary')
        
        # Agregar handler al logger raíz
        handler = RealTimeHandler(self)
        handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(handler)
    
    def add_log(self, log_entry):
        """Agregar entrada de log al buffer"""
        with self.lock:
            self.logs_buffer.append(log_entry)
            # Guardar en cache para acceso rápido
            cache.set('latest_logs', list(self.logs_buffer), 300)
    
    def get_recent_logs(self, limit=50, level_filter=None):
        """Obtener logs recientes"""
        with self.lock:
            logs = list(self.logs_buffer)
            
            # Filtrar por nivel si se especifica
            if level_filter:
                logs = [log for log in logs if log['level'] == level_filter]
            
            # Limitar cantidad
            return logs[-limit:]
    
    def get_logs_since(self, timestamp):
        """Obtener logs desde timestamp específico"""
        with self.lock:
            logs = []
            for log in self.logs_buffer:
                if log['timestamp'] > timestamp:
                    logs.append(log)
            return logs
    
    def log_scraping_event(self, event_type, data):
        """Log específico para eventos de scraping"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO',
            'message': f"SCRAPING: {event_type}",
            'module': 'scraper',
            'data': data,
            'color': 'text-success'
        }
        self.add_log(log_entry)
    
    def log_verification_event(self, hotel_name, success, details):
        """Log específico para verificación matemática"""
        level = 'INFO' if success else 'WARNING'
        color = 'text-success' if success else 'text-warning'
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': f"VERIFICACIÓN {hotel_name}: {'✅ EXITOSA' if success else '⚠️ FALLÓ'}",
            'module': 'verification',
            'data': details,
            'color': color
        }
        self.add_log(log_entry)

# Instancia global del logger
real_time_logger = RealTimeLogger()

def log_to_monitor(message, level='INFO', module='system', data=None):
    """Función helper para logging rápido"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'level': level,
        'message': message,
        'module': module,
        'data': data,
        'color': {
            'DEBUG': 'text-muted',
            'INFO': 'text-info',
            'WARNING': 'text-warning', 
            'ERROR': 'text-danger',
            'CRITICAL': 'text-danger'
        }.get(level, 'text-secondary')
    }
    real_time_logger.add_log(log_entry)

# Views para API
def get_real_time_logs(request):
    """API endpoint para obtener logs en tiempo real"""
    
    # Obtener parámetros
    limit = int(request.GET.get('limit', 50))
    level_filter = request.GET.get('level', None)
    since = request.GET.get('since', None)
    
    try:
        if since:
            logs = real_time_logger.get_logs_since(since)
        else:
            logs = real_time_logger.get_recent_logs(limit, level_filter)
        
        return JsonResponse({
            'success': True,
            'logs': logs,
            'total': len(logs),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def clear_logs(request):
    """Limpiar buffer de logs"""
    if request.method == 'POST':
        real_time_logger.logs_buffer.clear()
        cache.delete('latest_logs')
        log_to_monitor("Buffer de logs limpiado", 'INFO', 'system')
        
        return JsonResponse({
            'success': True,
            'message': 'Logs cleared successfully'
        })
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})
