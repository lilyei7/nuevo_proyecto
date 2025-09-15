"""
Integración entre OTASync y Scraping con Porcentaje de Precio
=============================================================

Este módulo mejora la integración entre el scraper inteligente y OTASync,
asegurando que los porcentajes de precio específicos de cada hotel se apliquen 
correctamente a los precios obtenidos del scraping.

Permite una sincronización más robusta y consistente con la API de OTASync.
"""

import os
import sys
import logging
import datetime
from typing import Dict, List, Union, Any

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tratar de usar SocketIO para logging en tiempo real si está disponible
try:
    from socket_manager import emit_log_message
    def emit_otasync_log(message, level='info', category='otasync'):
        emit_log_message(message, level, category)
except ImportError:
    def emit_otasync_log(message, level='info', category='otasync'):
        logger.log(getattr(logging, level.upper(), logging.INFO), message)

# Importar gestor existente de precios OTASync
try:
    from otasync_price_manager import OTASyncPriceManager as BasePriceManager
except ImportError as e:
    logger.error(f"Error importando OTASyncPriceManager: {e}")
    raise ImportError(f"No se pudo importar OTASyncPriceManager: {e}")

# Asegurar que también podemos usar OTASyncClient para compatibilidad
try:
    from otasync_client import OTASyncClient
except ImportError as e:
    logger.warning(f"No se pudo importar OTASyncClient: {e}")


class OTASyncScraperIntegration:
    """
    Integración mejorada entre scraper y OTASync con soporte de porcentajes
    
    Esta clase amplía la funcionalidad del gestor de precios de OTASync,
    añadiendo soporte para aplicar porcentajes específicos de hotel a los
    precios obtenidos por el scraper.
    """
    
    def __init__(self):
        """Inicializar integración OTASync-Scraper"""
        # Inicializar gestor base de precios
        self.price_manager = BasePriceManager()
        
        # También usar cliente tradicional para compatibilidad
        try:
            self.client = OTASyncClient()
            # Asegurar que el cliente está autenticado
            if hasattr(self.client, 'login') and not getattr(self.client, 'pkey', None):
                self.client.login()
        except Exception:
            self.client = None
            logger.warning("No se pudo inicializar OTASyncClient para compatibilidad")
        
        logger.info("Integración OTASync-Scraper inicializada")
        
    def sync_hotel_price(self, hotel: Dict[str, Any], 
                         check_in_date: Union[str, datetime.date],
                         check_out_date: Union[str, datetime.date],
                         price: float) -> bool:
        """
        Sincroniza el precio de un hotel con OTASync, aplicando el porcentaje configurado
        
        Args:
            hotel: Diccionario con información del hotel (debe incluir price_percent)
            check_in_date: Fecha de entrada
            check_out_date: Fecha de salida
            price: Precio base a sincronizar (sin porcentaje aplicado)
            
        Returns:
            bool: True si la sincronización fue exitosa
        """
        try:
            # Extraer datos del hotel
            hotel_name = hotel.get('hotel_name', hotel.get('name', 'Hotel desconocido'))
            otasync_property_id = hotel.get('otasync_property_id')
            otasync_room_type_id = hotel.get('otasync_room_type_id')
            price_percent = hotel.get('price_percent', 0)
            
            # Validar datos requeridos
            if not otasync_property_id or not otasync_room_type_id:
                logger.error(f"Faltan ID de OTASync para {hotel_name}")
                emit_otasync_log(f"❌ Faltan ID de OTASync para {hotel_name}", 'error')
                return False
            
            # Convertir fechas a formato string si son datetime
            if isinstance(check_in_date, datetime.date):
                check_in_str = check_in_date.strftime('%Y-%m-%d')
            else:
                check_in_str = str(check_in_date)
                
            if isinstance(check_out_date, datetime.date):
                check_out_str = check_out_date.strftime('%Y-%m-%d')
            else:
                check_out_str = str(check_out_date)
            
            # Convertir todo a float para evitar problemas con Decimal
            price_float = float(price)
            percent_float = float(price_percent)
            
            # Calcular precio final con el porcentaje
            final_price = price_float * (1 + percent_float / 100)
            
            logger.info(f"Sincronizando precio para {hotel_name} ({check_in_str})")
            logger.info(f"- Precio base: ${price_float:.2f}")
            logger.info(f"- Porcentaje: {percent_float:.1f}%")
            logger.info(f"- Precio final: ${final_price:.2f}")
            
            emit_otasync_log(f"🔄 Actualizando precio: {check_in_str}", 'info')
            
            # Método 1: Usar OTASync client si está disponible (mejor)
            if self.client and hasattr(self.client, 'sync_price'):
                success = self.client.sync_price(
                    property_id=otasync_property_id,
                    room_type_id=otasync_room_type_id,
                    check_in=check_in_str,
                    check_out=check_out_str,
                    price=final_price,
                    variation_type=0  # 0 = Precio exacto
                )
            # Método 2: Usar el price manager
            else:
                # Para compatibilidad con el price manager, crear estructura de habitaciones
                rooms = [{
                    "id_room_types": int(otasync_room_type_id),
                    "value": final_price
                }]
                
                # Actualizar el precio utilizando el price manager
                success = self.price_manager.edit_prices(
                    property_id=int(otasync_property_id),
                    pricing_plan_id=int(otasync_room_type_id),
                    date_from=check_in_str,
                    date_to=check_out_str,
                    rooms=rooms,
                    variation_type=0  # Precio exacto
                )
            
            if success:
                emit_otasync_log(f"✅ Sincronizado: {check_in_str} - ${final_price:.2f}", 'success')
                logger.info(f"✅ Precio sincronizado: ${final_price:.2f}")
                return True
            else:
                emit_otasync_log(f"❌ Error sincronizando: {check_in_str}", 'error')
                logger.error(f"Error sincronizando precio para {hotel_name}")
                return False
                
        except Exception as e:
            emit_otasync_log(f"❌ Error: {str(e)}", 'error')
            logger.exception(f"Error en sync_hotel_price: {e}")
            return False

    def bulk_sync_prices(self, hotel: Dict[str, Any], 
                         prices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sincroniza varios precios en lote para un hotel
        
        Args:
            hotel: Diccionario con información del hotel
            prices: Lista de diccionarios con precios:
                   [{'checkin_date': '2023-01-01', 'checkout_date': '2023-01-02', 'price': 100.0}, ...]
                
        Returns:
            dict: Resultado de la sincronización
        """
        try:
            # Extraer datos del hotel
            hotel_name = hotel.get('hotel_name', hotel.get('name', 'Hotel desconocido'))
            otasync_property_id = hotel.get('otasync_property_id')
            otasync_room_type_id = hotel.get('otasync_room_type_id')
            price_percent = float(hotel.get('price_percent', 0))
            
            # Validar datos requeridos
            if not otasync_property_id or not otasync_room_type_id:
                logger.error(f"Faltan ID de OTASync para {hotel_name}")
                emit_otasync_log(f"❌ Faltan ID de OTASync para {hotel_name}", 'error')
                return {
                    "success": False,
                    "error": "Faltan IDs de OTASync",
                    "synced_count": 0,
                    "failed_count": len(prices)
                }
            
            # Crear estructura de fechas y precios
            date_prices = []
            for price_data in prices:
                base_price = float(price_data.get('price', 0))
                
                # Aplicar porcentaje al precio base
                final_price = base_price * (1 + price_percent / 100)
                
                # Añadir al array para actualización en lote
                date_prices.append({
                    'date': price_data.get('checkin_date'),
                    'price': final_price
                })
            
            logger.info(f"Actualizando {len(date_prices)} precios en lote para {hotel_name}")
            logger.info(f"- Porcentaje aplicado: {price_percent:.1f}%")
            emit_otasync_log(f"🔄 Actualizando {len(date_prices)} precios en lote", 'info')
            
            # Método 1: Si tenemos acceso al cliente OTASync, usarlo directamente
            success = False
            if self.client and hasattr(self.client, 'update_pricing_official'):
                try:
                    result = self.client.update_pricing_official(
                        property_id=otasync_property_id,
                        room_type_id=otasync_room_type_id,
                        date_prices=date_prices,
                        variation_type=0  # Precio exacto
                    )
                    success = bool(result and result.get('success', False))
                except Exception as e:
                    logger.error(f"Error usando update_pricing_official: {e}")
                    success = False
            
            # Método 2: Si no funcionó, intentar con price_manager
            if not success:
                logger.info("Usando método alternativo para actualización en lote")
                
                # Crear un nuevo formato compatible con price_manager
                from_date = date_prices[0]['date']
                to_date = date_prices[-1]['date']
                
                rooms = [{
                    "id_room_types": int(otasync_room_type_id),
                    "value": date_prices[0]['price']  # Usar primer precio como referencia
                }]
                
                # Actualizar cada fecha por separado (menos eficiente pero más compatible)
                success_count = 0
                for dp in date_prices:
                    rooms[0]['value'] = dp['price']  # Actualizar precio
                    single_success = self.price_manager.edit_prices(
                        property_id=int(otasync_property_id),
                        pricing_plan_id=int(otasync_room_type_id),
                        date_from=dp['date'],
                        date_to=dp['date'],
                        rooms=rooms,
                        variation_type=0
                    )
                    if single_success:
                        success_count += 1
                
                success = success_count > 0
                
            if success:
                logger.info(f"✅ Actualización en lote exitosa")
                emit_otasync_log(f"✅ {len(date_prices)} precios sincronizados con OTASync", 'success')
                return {
                    "success": True,
                    "synced_count": len(date_prices),
                    "failed_count": 0
                }
            else:
                logger.error(f"❌ Error en actualización en lote")
                emit_otasync_log(f"❌ Error sincronizando precios en lote", 'error')
                return {
                    "success": False,
                    "error": "Falló la actualización en lote",
                    "synced_count": 0,
                    "failed_count": len(date_prices)
                }
                
        except Exception as e:
            logger.exception(f"Error en bulk_sync_prices: {e}")
            emit_otasync_log(f"❌ Error: {str(e)}", 'error')
            return {
                "success": False,
                "error": str(e),
                "synced_count": 0,
                "failed_count": len(prices) if prices else 0
            }

# Función simplificada para uso externo
def sync_hotel_price_with_percentage(property_id, room_type_id, check_in, check_out, base_price, percentage):
    """
    Función simplificada para sincronizar precio con porcentaje
    
    Args:
        property_id: ID de la propiedad en OTASync
        room_type_id: ID del tipo de habitación
        check_in: Fecha de entrada (YYYY-MM-DD)
        check_out: Fecha de salida (YYYY-MM-DD) 
        base_price: Precio base
        percentage: Porcentaje a aplicar (25.0 = 25%)
        
    Returns:
        bool: True si la sincronización fue exitosa
    """
    try:
        # Crear hotel simplificado
        hotel = {
            'otasync_property_id': property_id,
            'otasync_room_type_id': room_type_id,
            'price_percent': percentage,
            'name': f"Property {property_id}"
        }
        
        # Usar la integración para sincronizar
        integration = OTASyncScraperIntegration()
        return integration.sync_hotel_price(
            hotel=hotel,
            check_in_date=check_in,
            check_out_date=check_out,
            price=base_price
        )
    except Exception as e:
        logger.exception(f"Error en sync_hotel_price_with_percentage: {e}")
        return False

# Función para actualizar precios en lote simplificada
def bulk_sync_prices_with_percentage(property_id, room_type_id, prices, percentage):
    """
    Sincroniza múltiples precios en lote aplicando un porcentaje
    
    Args:
        property_id: ID de la propiedad
        room_type_id: ID del tipo de habitación
        prices: Lista de diccionarios con fechas y precios
                [{'checkin_date': '2023-01-01', 'price': 100.0}, ...]
        percentage: Porcentaje a aplicar (25.0 = 25%)
        
    Returns:
        dict: Resultado de la sincronización
    """
    try:
        # Crear hotel simplificado
        hotel = {
            'otasync_property_id': property_id,
            'otasync_room_type_id': room_type_id,
            'price_percent': percentage,
            'name': f"Property {property_id}"
        }
        
        # Usar la integración para sincronización en lote
        integration = OTASyncScraperIntegration()
        return integration.bulk_sync_prices(hotel, prices)
    except Exception as e:
        logger.exception(f"Error en bulk_sync_prices_with_percentage: {e}")
        return {
            "success": False,
            "error": str(e),
            "synced_count": 0,
            "failed_count": len(prices) if prices else 0
        }

# Verificar integración si se ejecuta directamente
if __name__ == "__main__":
    # Configuración de prueba
    property_id = "9355"  # Ejemplo
    room_type_id = "29119"  # Ejemplo
    check_in = datetime.date.today().strftime('%Y-%m-%d')
    check_out = check_in
    base_price = 3200.0
    percentage = 25.0
    
    print(f"🧪 TEST: Sincronizando precio con {percentage}% para {check_in}")
    print(f"- Precio base: ${base_price}")
    
    # Ejecutar prueba
    result = sync_hotel_price_with_percentage(
        property_id=property_id,
        room_type_id=room_type_id,
        check_in=check_in,
        check_out=check_out,
        base_price=base_price,
        percentage=percentage
    )
    
    print(f"Resultado: {'✅ Éxito' if result else '❌ Error'}")
    
    # Prueba de actualización en lote
    prices = [
        {"checkin_date": check_in, "price": base_price},
        {"checkin_date": (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d'), "price": base_price},
        {"checkin_date": (datetime.date.today() + datetime.timedelta(days=2)).strftime('%Y-%m-%d'), "price": base_price}
    ]
    
    print(f"🧪 TEST: Sincronizando {len(prices)} precios en lote con {percentage}%")
    batch_result = bulk_sync_prices_with_percentage(
        property_id=property_id,
        room_type_id=room_type_id,
        prices=prices,
        percentage=percentage
    )
    
    print(f"Resultado batch: {'✅ Éxito' if batch_result.get('success') else '❌ Error'}")
    print(f"- Sincronizados: {batch_result.get('synced_count', 0)}")
    print(f"- Fallidos: {batch_result.get('failed_count', 0)}")
