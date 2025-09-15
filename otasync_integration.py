#!/usr/bin/env python3
"""
OTASync Integration for Django Hotel Scraper
Sistema completo para integración de precios con la API de OTASync
"""

try:
    from .otasync_client import OTASyncClient
except ImportError:
    from otasync_client import OTASyncClient
import logging
import datetime

# Django imports con fallback para casos donde no hay settings configurados
try:
    from django.utils import timezone
    from django.conf import settings
except Exception:
    # Fallback si Django settings no están configurados
    class FallbackTimezone:
        @staticmethod
        def now():
            return datetime.datetime.now()
    timezone = FallbackTimezone()
    settings = None

logger = logging.getLogger(__name__)


class OTASyncIntegration:
    """Clase principal para integración con OTASync"""
    
    def __init__(self, test_mode=False):
        """Inicializar integración OTASync"""
        # Cargar credenciales manualmente si se ejecuta fuera del entorno Django
        creds = self._load_credentials()
        
        # Inicializar cliente con credenciales si están disponibles
        if creds and 'token' in creds and 'username' in creds and 'password' in creds:
            self.client = OTASyncClient(
                email=creds['username'],
                password=creds['password'],
                token=creds['token']
            )
        else:
            self.client = OTASyncClient()
            
        self.connected = False
        self.use_variation_type = True  # Usar método de variation_type=1 para porcentajes
        self.test_mode = test_mode
        logger.info("🔗 OTASync Integration iniciada")
    
    def _load_credentials(self):
        """Cargar credenciales desde archivo de configuración"""
        creds = {}
        try:
            # Intentar primero con path relativo a este archivo
            import os
            base_dir = os.path.dirname(os.path.abspath(__file__))
            kunas_path = os.path.join(os.path.dirname(base_dir), 'kunas', 'credentials.txt')
            
            # Alternativa para pruebas directas
            if not os.path.exists(kunas_path):
                kunas_path = os.path.join(base_dir, 'kunas', 'credentials.txt')
            
            if os.path.exists(kunas_path):
                with open(kunas_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            creds[key] = value
                logger.info(f"✅ Credenciales OTASync cargadas desde {kunas_path}")
            else:
                logger.warning(f"⚠️ Archivo de credenciales no encontrado: {kunas_path}")
        except Exception as e:
            logger.warning(f"⚠️ Error cargando credenciales: {e}")
        
        return creds
    
    def connect(self) -> bool:
        """Conectar con OTASync"""
        try:
            # El OTASyncClient ya intenta el login automáticamente en __init__
            # Solo necesitamos verificar si tiene auth_token
            if hasattr(self.client, 'auth_token') and self.client.auth_token:
                self.connected = True
                logger.info("✅ Conectado exitosamente a OTASync")
                return True
            else:
                # Intentar login manual si no se conectó automáticamente
                success = self.client.login()
                self.connected = success
                if success:
                    logger.info("✅ Conectado exitosamente a OTASync")
                else:
                    logger.error("❌ Error conectando a OTASync")
                return success
        except Exception as e:
            logger.error(f"❌ Error en conexión OTASync: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Probar conexión con OTASync"""
        try:
            return self.client.test_connection()
        except Exception as e:
            logger.error(f"❌ Error probando conexión OTASync: {e}")
            return False
    
    def get_properties(self) -> list:
        """Obtener todas las propiedades de OTASync"""
        try:
            if not self.connected:
                if not self.connect():
                    return []
            
            properties = self.client.get_properties()
            logger.info(f"📊 Obtenidas {len(properties)} propiedades de OTASync")
            return properties
        except Exception as e:
            logger.error(f"❌ Error obteniendo propiedades: {e}")
            return []
    
    def sync_hotel_price(self, hotel, check_in_date, check_out_date, price) -> bool:
        """Sincronizar precio de hotel con OTASync"""
        try:
            # Manejar tanto objetos como diccionarios
            if isinstance(hotel, dict):
                hotel_name = hotel.get('name', 'Hotel desconocido')
                otasync_enabled = hotel.get('otasync_enabled', False)
                otasync_property_id = hotel.get('otasync_property_id')
                otasync_room_type_id = hotel.get('otasync_room_type_id')
                price_percent = hotel.get('price_percent', 0)
            else:
                hotel_name = hotel.name
                otasync_enabled = hotel.otasync_enabled
                otasync_property_id = hotel.otasync_property_id
                otasync_room_type_id = hotel.otasync_room_type_id
                price_percent = hotel.price_percent
            
            if not otasync_enabled:
                logger.warning(f"🔄 Hotel {hotel_name} no tiene OTASync habilitado")
                return False
            
            if not otasync_property_id or not otasync_room_type_id:
                logger.warning(f"🔄 Hotel {hotel_name} no tiene configuración OTASync completa")
                return False
            
            if not self.connected:
                if not self.connect():
                    return False
            
            # Convertir todo a float para evitar problemas con Decimal
            price_float = float(price)
            percent_float = float(price_percent)
            
            # SOLUCIÓN CORREGIDA: Calcular el precio final con el porcentaje y enviarlo como precio exacto
            # El problema anterior era que se enviaba el porcentaje como precio cuando se usaba variation_type=1
            # lo que causaba que se mostrara el porcentaje mismo como precio en el calendario
            
            if percent_float > 0:
                # Calcular el precio final con el porcentaje aplicado
                final_price = price_float * (1 + percent_float/100)
                
                logger.info(f"📊 OTASync: Aplicando porcentaje {percent_float}% sobre precio base ${price_float}")
                logger.info(f"📊 OTASync: Precio final calculado: ${final_price}")
                
                # Enviar el precio final calculado como precio exacto
                success = self.client.sync_price(
                    property_id=otasync_property_id,
                    room_type_id=otasync_room_type_id,
                    check_in=check_in_date.strftime('%Y-%m-%d'),
                    check_out=check_out_date.strftime('%Y-%m-%d'),
                    price=final_price,  # Enviar el precio final calculado
                    variation_type=0,  # 0 = Establecer precio exacto (más seguro)
                )
            else:
                # Si no hay porcentaje, simplemente establecer el precio exacto
                logger.info(f"📊 OTASync: Estableciendo precio exacto ${price_float}")
                
                success = self.client.sync_price(
                    property_id=otasync_property_id,
                    room_type_id=otasync_room_type_id,
                    check_in=check_in_date.strftime('%Y-%m-%d'),
                    check_out=check_out_date.strftime('%Y-%m-%d'),
                    price=price_float,
                    variation_type=0  # 0 = Establecer precio exacto
                )
            
            if success:
                # Solo actualizar timestamp si es un objeto modelo de Django
                if not isinstance(hotel, dict):
                    try:
                        hotel.last_sync = timezone.now()
                        hotel.save(update_fields=['last_sync'])
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo actualizar last_sync: {e}")
                
                # Mostrar precio esperado después de aplicar porcentaje
                if percent_float > 0:
                    expected_price = price_float * (1 + percent_float/100)
                    logger.info(f"✅ Precio sincronizado para {hotel_name}: ${price_float} + {percent_float}% = ${expected_price}")
                else:
                    logger.info(f"✅ Precio sincronizado para {hotel_name}: ${price_float}")
                    
                return True
            else:
                logger.error(f"❌ Error sincronizando precio para {hotel_name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en sync_hotel_price para {hotel_name if 'hotel_name' in locals() else 'hotel'}: {e}")
            return False
    
    def bulk_sync_prices(self, scraping_results) -> dict:
        """Sincronizar múltiples precios en lote"""
        sync_stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        
        try:
            if not self.connected:
                if not self.connect():
                    logger.error("❌ No se pudo conectar a OTASync para sincronización masiva")
                    return sync_stats
            
            for result in scraping_results:
                sync_stats['total'] += 1
                
                if not result.hotel.otasync_enabled:
                    sync_stats['skipped'] += 1
                    continue
                
                if not result.price:
                    sync_stats['skipped'] += 1
                    continue
                
                success = self.sync_hotel_price(
                    hotel=result.hotel,
                    check_in_date=result.check_in,
                    check_out_date=result.check_out,
                    price=result.price
                )
                
                if success:
                    sync_stats['success'] += 1
                    # Marcar como sincronizado
                    result.otasync_synced = True
                    result.otasync_sync_at = timezone.now()
                    result.save(update_fields=['otasync_synced', 'otasync_sync_at'])
                else:
                    sync_stats['failed'] += 1
            
            logger.info(f"📊 Sincronización masiva completada: {sync_stats}")
            return sync_stats
            
        except Exception as e:
            logger.error(f"❌ Error en sincronización masiva: {e}")
            return sync_stats
    
    def get_sync_status(self) -> dict:
        """Obtener estado de sincronización"""
        try:
            from hotels.models import Hotel, ScrapingResult
            
            status = {
                'otasync_connected': self.test_connection(),
                'total_hotels': Hotel.objects.count(),
                'otasync_enabled_hotels': Hotel.objects.filter(otasync_enabled=True).count(),
                'pending_sync_results': ScrapingResult.objects.filter(
                    otasync_synced=False,
                    hotel__otasync_enabled=True,
                    status='success'
                ).count(),
                'last_connection_test': timezone.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado de sincronización: {e}")
            return {
                'otasync_connected': False,
                'total_hotels': 0,
                'otasync_enabled_hotels': 0,
                'pending_sync_results': 0,
                'error': str(e)
            }


# Función de sincronización para integrarse con scraper/db.py
def sync_scraped_price_to_otasync(hotel_id, checkin_date, price_amount, base_price=None, taxes=None, db_manager=None, log_callback=None):
    """
    Sincroniza el precio scrapeado con OTASync
    
    Args:
        hotel_id: ID del hotel en la base de datos
        checkin_date: Fecha de check-in (formato YYYY-MM-DD)
        price_amount: Precio final (con margen aplicado)
        base_price: Precio base (opcional)
        taxes: Impuestos (opcional)
        db_manager: Instancia del manejador de base de datos
        log_callback: Función para emitir logs
        
    Returns:
        bool: True si la sincronización fue exitosa
    """
    try:
        integration = OTASyncIntegration()
        
        if log_callback:
            log_callback("🔄 Iniciando sincronización con OTASync...", 'info', 'otasync')
            
        # Obtener información del hotel de la base de datos
        hotel_info = None
        if db_manager:
            hotel_info = db_manager.get_hotel_otasync_info(hotel_id)
            
        if not hotel_info:
            if log_callback:
                log_callback(f"⚠️ Hotel {hotel_id} no encontrado en la base de datos", 'warning', 'otasync')
            return False
            
        if not hotel_info.get('otasync_property_id'):
            if log_callback:
                log_callback(f"⚠️ Hotel {hotel_id} no tiene configuración de property_id para OTASync", 'warning', 'otasync')
            return False
            
        if not hotel_info.get('otasync_room_type_id'):
            if log_callback:
                log_callback(f"⚠️ Hotel {hotel_id} no tiene configuración de room_type_id para OTASync", 'warning', 'otasync')
            return False
            
        # Calcular checkout sumando 1 día
        from datetime import datetime, timedelta
        checkin = datetime.strptime(checkin_date, "%Y-%m-%d")
        checkout = (checkin + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Sincronizar el precio
        return integration.sync_hotel_price(
            hotel={
                'id': hotel_id,
                'name': hotel_info.get('name', f'Hotel ID {hotel_id}'),
                'otasync_property_id': hotel_info.get('otasync_property_id'),
                'otasync_room_type_id': hotel_info.get('otasync_room_type_id')
            },
            check_in_date=checkin_date,
            check_out_date=checkout,
            price=price_amount
        )
    except Exception as e:
        logger.error(f"❌ Error en sync_scraped_price_to_otasync: {e}")
        if log_callback:
            log_callback(f"❌ Error sincronizando con OTASync: {str(e)}", 'error', 'otasync')
        return False

# Instancia global para uso en vistas
otasync_integration = OTASyncIntegration()
