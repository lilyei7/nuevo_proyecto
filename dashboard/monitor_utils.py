#!/usr/bin/env python3
"""
🔧 UTILIDADES PARA LOGGING INTEGRADO
===================================

Helper functions para agregar logs al monitor integrado
sin necesidad de servidores adicionales.
"""

import json
from datetime import datetime
from django.core.cache import cache
from typing import Dict, List, Optional

class MonitorLogger:
    """Logger integrado para el monitor en tiempo real"""
    
    def __init__(self):
        self.cache_key = 'realtime_logs'
        self.max_logs = 500
    
    def add_log(self, message: str, level: str = 'INFO', module: str = 'system', data: Optional[Dict] = None):
        """
        Agregar un log al monitor en tiempo real
        
        Args:
            message: Mensaje del log
            level: Nivel del log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            module: Módulo que genera el log
            data: Datos adicionales (opcional)
        """
        try:
            # Obtener logs existentes del cache
            logs = cache.get(self.cache_key, [])
            
            # Crear nueva entrada de log
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': level.upper(),
                'message': message,
                'module': module,
                'color': self.get_level_color(level),
                'data': data
            }
            
            # Agregar al buffer
            logs.append(log_entry)
            
            # Mantener límite de logs
            if len(logs) > self.max_logs:
                logs = logs[-self.max_logs:]
            
            # Guardar en cache
            cache.set(self.cache_key, logs, 600)  # 10 minutos de cache
            
            # También log al sistema Django
            import logging
            django_logger = logging.getLogger(module)
            
            if level.upper() == 'DEBUG':
                django_logger.debug(message)
            elif level.upper() == 'INFO':
                django_logger.info(message)
            elif level.upper() == 'WARNING':
                django_logger.warning(message)
            elif level.upper() == 'ERROR':
                django_logger.error(message)
            elif level.upper() == 'CRITICAL':
                django_logger.critical(message)
            
        except Exception as e:
            # Fallback: al menos log al sistema Django
            import logging
            logging.error(f"Error agregando log al monitor: {e}")
    
    def get_level_color(self, level: str) -> str:
        """Obtener color CSS para el nivel de log"""
        colors = {
            'DEBUG': 'text-muted',
            'INFO': 'text-info',
            'WARNING': 'text-warning',
            'ERROR': 'text-danger',
            'CRITICAL': 'text-danger'
        }
        return colors.get(level.upper(), 'text-secondary')
    
    def log_scraping_start(self, hotel_name: str, url: str):
        """Log específico para inicio de scraping"""
        self.add_log(
            f"🔍 Iniciando scraping: {hotel_name}",
            'INFO',
            'scraper',
            {'hotel': hotel_name, 'url': url}
        )
    
    def log_scraping_success(self, hotel_name: str, price: float, base_price: float, taxes: float):
        """Log específico para scraping exitoso"""
        self.add_log(
            f"✅ Scraping exitoso: {hotel_name} - ${price:.2f} MXN",
            'INFO',
            'scraper',
            {
                'hotel': hotel_name,
                'final_price': price,
                'base_price': base_price,
                'taxes': taxes
            }
        )
    
    def log_scraping_error(self, hotel_name: str, error: str):
        """Log específico para errores de scraping"""
        self.add_log(
            f"❌ Error scraping {hotel_name}: {error}",
            'ERROR',
            'scraper',
            {'hotel': hotel_name, 'error': error}
        )
    
    def log_verification_success(self, hotel_name: str, calculations: Dict):
        """Log específico para verificación matemática exitosa"""
        self.add_log(
            f"🧮 Verificación exitosa: {hotel_name}",
            'INFO',
            'verification',
            calculations
        )
    
    def log_verification_error(self, hotel_name: str, errors: List[str]):
        """Log específico para errores de verificación"""
        self.add_log(
            f"⚠️ Error verificación {hotel_name}: {', '.join(errors)}",
            'WARNING',
            'verification',
            {'hotel': hotel_name, 'errors': errors}
        )
    
    def log_system_event(self, event: str, details: Optional[Dict] = None):
        """Log específico para eventos del sistema"""
        self.add_log(
            f"🔧 Sistema: {event}",
            'INFO',
            'system',
            details
        )
    
    def clear_logs(self):
        """Limpiar todos los logs del cache"""
        try:
            cache.delete(self.cache_key)
            self.add_log("🗑️ Buffer de logs limpiado", 'INFO', 'system')
            return True
        except Exception as e:
            import logging
            logging.error(f"Error limpiando logs: {e}")
            return False
    
    def get_logs(self, limit: int = 50, level_filter: Optional[str] = None, since: Optional[str] = None) -> List[Dict]:
        """
        Obtener logs del cache
        
        Args:
            limit: Número máximo de logs a devolver
            level_filter: Filtrar por nivel específico
            since: Obtener logs desde timestamp específico
            
        Returns:
            Lista de logs
        """
        try:
            logs = cache.get(self.cache_key, [])
            
            # Filtrar por timestamp si se especifica
            if since:
                logs = [log for log in logs if log['timestamp'] > since]
            
            # Filtrar por nivel si se especifica
            if level_filter:
                logs = [log for log in logs if log['level'] == level_filter.upper()]
            
            # Limitar cantidad
            return logs[-limit:]
            
        except Exception as e:
            import logging
            logging.error(f"Error obteniendo logs: {e}")
            return []

# Instancia global del logger
monitor_logger = MonitorLogger()

# Funciones de conveniencia para uso rápido
def log_to_monitor(message: str, level: str = 'INFO', module: str = 'system', data: Optional[Dict] = None):
    """Función helper para logging rápido al monitor"""
    monitor_logger.add_log(message, level, module, data)

def log_scraping_event(event_type: str, hotel_name: str, data: Optional[Dict] = None):
    """Función helper para eventos de scraping"""
    if event_type == 'start':
        monitor_logger.log_scraping_start(hotel_name, data.get('url', '') if data else '')
    elif event_type == 'success':
        monitor_logger.log_scraping_success(
            hotel_name, 
            data.get('price', 0) if data else 0,
            data.get('base_price', 0) if data else 0,
            data.get('taxes', 0) if data else 0
        )
    elif event_type == 'error':
        monitor_logger.log_scraping_error(hotel_name, data.get('error', 'Error desconocido') if data else 'Error desconocido')

def log_verification_event(success: bool, hotel_name: str, data: Optional[Dict] = None):
    """Función helper para eventos de verificación"""
    if success:
        monitor_logger.log_verification_success(hotel_name, data or {})
    else:
        monitor_logger.log_verification_error(hotel_name, data.get('errors', []) if data else ['Error desconocido'])

# Ejemplo de uso:
# from dashboard.monitor_utils import log_to_monitor, log_scraping_event, log_verification_event
# 
# # Log básico
# log_to_monitor("Sistema iniciado", "INFO", "system")
# 
# # Log de scraping
# log_scraping_event("start", "Hotel Premium", {"url": "https://example.com"})
# log_scraping_event("success", "Hotel Premium", {"price": 1628.64, "base_price": 1080.00, "taxes": 172.80})
# 
# # Log de verificación
# log_verification_event(True, "Hotel Premium", {"calculations": {...}})
