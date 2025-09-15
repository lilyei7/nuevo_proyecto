#!/usr/bin/env python3
"""
Integración Oficial OTASync-Scraper
===================================

Este módulo integra el scraper inteligente con el cliente oficial de OTASync,
usando las credenciales correctas y la API oficial.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importar cliente oficial de OTASync
try:
    from otasync_api_client_official import OTASyncAPIClient
except ImportError:
    print("❌ Error: No se puede importar OTASyncAPIClient")
    sys.exit(1)

# Importar sistema de WebSocket para logs en tiempo real (opcional)
try:
    from socket_manager import emit_log_message
    def emit_integration_log(message, level='info', category='integration'):
        emit_log_message(message, level, category)
        logger.info(f"[{category}] {message}")
except ImportError:
    def emit_integration_log(message, level='info', category='integration'):
        logger.log(getattr(logging, level.upper(), logging.INFO), f"[{category}] {message}")


class OfficialScrapingIntegration:
    """
    Integración oficial entre scraper y OTASync
    
    Esta clase maneja la sincronización de precios scraped con OTASync
    usando el cliente oficial y las credenciales correctas.
    """
    
    def __init__(self):
        """Inicializar integración"""
        self.otasync_client = OTASyncAPIClient()
        self.connected = self.otasync_client.test_connection()
        
        emit_integration_log("Integración oficial OTASync-Scraper iniciada")
        emit_integration_log(f"Estado de conexión: {'✅ Conectado' if self.connected else '❌ Desconectado'}")
    
    def sync_scraped_price(self, hotel_info: Dict[str, Any], scraped_price: float, 
                          check_in_date: str, apply_margin: bool = True) -> bool:
        """
        Sincronizar precio scraped con OTASync
        
        Args:
            hotel_info: Información del hotel con IDs de OTASync
            scraped_price: Precio obtenido del scraping
            check_in_date: Fecha de check-in (YYYY-MM-DD)
            apply_margin: Si aplicar margen/porcentaje configurado
            
        Returns:
            bool: True si la sincronización fue exitosa
        """
        try:
            if not self.connected:
                emit_integration_log("❌ No hay conexión con OTASync", "error")
                return False
            
            # Verificar que tenemos los IDs necesarios
            required_fields = ['otasync_property_id', 'otasync_pricing_plan_id', 'otasync_room_type_id']
            missing_fields = []
            
            for field in required_fields:
                if not hotel_info.get(field):
                    missing_fields.append(field)
            
            if missing_fields:
                emit_integration_log(f"❌ Faltan campos requeridos: {missing_fields}", "error")
                return False
            
            # Calcular precio final
            final_price = scraped_price
            if apply_margin and hotel_info.get('price_percent'):
                try:
                    margin_percent = float(hotel_info['price_percent'])
                    final_price = scraped_price * (1 + margin_percent / 100)
                    emit_integration_log(f"💰 Aplicando margen {margin_percent}%: ${scraped_price:.2f} → ${final_price:.2f}")
                except (ValueError, TypeError):
                    emit_integration_log(f"⚠️ Error aplicando margen, usando precio original", "warning")
            
            # Sincronizar con OTASync
            emit_integration_log(f"🔄 Sincronizando precio ${final_price:.2f} para {check_in_date}")
            
            success = self.otasync_client.update_single_room_price(
                property_id=int(hotel_info['otasync_property_id']),
                pricing_plan_id=int(hotel_info['otasync_pricing_plan_id']),
                room_type_id=int(hotel_info['otasync_room_type_id']),
                price=final_price,
                date_from=check_in_date,
                date_to=check_in_date  # Una sola noche
            )
            
            if success:
                emit_integration_log(f"✅ Precio sincronizado exitosamente: ${final_price:.2f}")
                return True
            else:
                emit_integration_log(f"❌ Error sincronizando precio", "error")
                return False
                
        except Exception as e:
            emit_integration_log(f"❌ Excepción sincronizando precio: {e}", "error")
            return False
    
    def bulk_sync_scraped_prices(self, hotel_info: Dict[str, Any], 
                                scraped_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sincronizar múltiples precios scraped en lote
        
        Args:
            hotel_info: Información del hotel
            scraped_results: Lista de resultados del scraping con 'date' y 'price'
            
        Returns:
            Dict con estadísticas del proceso
        """
        try:
            if not self.connected:
                emit_integration_log("❌ No hay conexión con OTASync", "error")
                return {'success': False, 'error': 'No connection'}
            
            emit_integration_log(f"📦 Iniciando sincronización en lote de {len(scraped_results)} precios")
            
            # Preparar datos para actualización en lote
            date_prices = []
            for result in scraped_results:
                if 'date' in result and 'price' in result and result['price'] > 0:
                    # Aplicar margen si está configurado
                    final_price = result['price']
                    if hotel_info.get('price_percent'):
                        try:
                            margin_percent = float(hotel_info['price_percent'])
                            final_price = result['price'] * (1 + margin_percent / 100)
                        except (ValueError, TypeError):
                            pass
                    
                    date_prices.append({
                        'date': result['date'],
                        'price': final_price
                    })
            
            if not date_prices:
                emit_integration_log("❌ No hay precios válidos para sincronizar", "error")
                return {'success': False, 'error': 'No valid prices'}
            
            # Realizar sincronización en lote
            bulk_result = self.otasync_client.update_bulk_prices(
                property_id=int(hotel_info['otasync_property_id']),
                pricing_plan_id=int(hotel_info['otasync_pricing_plan_id']),
                room_type_id=int(hotel_info['otasync_room_type_id']),
                date_prices=date_prices
            )
            
            emit_integration_log(f"📊 Resultado: {bulk_result['success']} éxitos, {bulk_result['failed']} fallos")
            
            return {
                'success': bulk_result['success'] > 0,
                'total': bulk_result['total'],
                'success_count': bulk_result['success'],
                'failed_count': bulk_result['failed'],
                'errors': bulk_result.get('errors', [])
            }
            
        except Exception as e:
            emit_integration_log(f"❌ Error en sincronización en lote: {e}", "error")
            return {'success': False, 'error': str(e)}
    
    def get_current_prices(self, hotel_info: Dict[str, Any], days: int = 7) -> Dict[str, Any]:
        """
        Obtener precios actuales de OTASync para un hotel
        
        Args:
            hotel_info: Información del hotel
            days: Número de días hacia adelante
            
        Returns:
            Dict con precios actuales
        """
        try:
            if not self.connected:
                return {}
            
            date_from = datetime.now().strftime('%Y-%m-%d')
            date_to = (datetime.now() + timedelta(days=days-1)).strftime('%Y-%m-%d')
            
            prices = self.otasync_client.get_prices(
                property_id=int(hotel_info['otasync_property_id']),
                pricing_plan_id=int(hotel_info['otasync_pricing_plan_id']),
                date_from=date_from,
                date_to=date_to
            )
            
            return prices
            
        except Exception as e:
            emit_integration_log(f"❌ Error obteniendo precios actuales: {e}", "error")
            return {}
    
    def verify_price_sync(self, hotel_info: Dict[str, Any], expected_price: float, 
                         check_date: str) -> bool:
        """
        Verificar que un precio se sincronizó correctamente
        
        Args:
            hotel_info: Información del hotel
            expected_price: Precio esperado
            check_date: Fecha a verificar
            
        Returns:
            bool: True si el precio coincide
        """
        try:
            current_prices = self.get_current_prices(hotel_info, days=1)
            room_type_id = str(hotel_info['otasync_room_type_id'])
            
            if room_type_id in current_prices and check_date in current_prices[room_type_id]:
                actual_price = float(current_prices[room_type_id][check_date])
                price_diff = abs(actual_price - expected_price)
                
                # Permitir una pequeña diferencia por redondeo
                if price_diff < 0.01:
                    emit_integration_log(f"✅ Precio verificado: ${actual_price:.2f}")
                    return True
                else:
                    emit_integration_log(f"❌ Precio no coincide: esperado ${expected_price:.2f}, actual ${actual_price:.2f}")
                    return False
            else:
                emit_integration_log(f"❌ No se encontró precio para verificar")
                return False
                
        except Exception as e:
            emit_integration_log(f"❌ Error verificando precio: {e}", "error")
            return False


# Funciones auxiliares para integración con el scraper existente
def sync_single_scraped_price(property_id, pricing_plan_id, room_type_id, 
                             scraped_price, check_in_date, margin_percent=0):
    """
    Función simplificada para sincronizar un precio scraped
    
    Args:
        property_id: ID de la propiedad en OTASync
        pricing_plan_id: ID del plan de precios
        room_type_id: ID del tipo de habitación
        scraped_price: Precio obtenido del scraping
        check_in_date: Fecha de check-in (YYYY-MM-DD)
        margin_percent: Porcentaje de margen a aplicar
        
    Returns:
        bool: True si la sincronización fue exitosa
    """
    hotel_info = {
        'otasync_property_id': property_id,
        'otasync_pricing_plan_id': pricing_plan_id,
        'otasync_room_type_id': room_type_id,
        'price_percent': margin_percent
    }
    
    integration = OfficialScrapingIntegration()
    return integration.sync_scraped_price(hotel_info, scraped_price, check_in_date)


def sync_bulk_scraped_prices(property_id, pricing_plan_id, room_type_id, 
                           scraped_results, margin_percent=0):
    """
    Función simplificada para sincronizar múltiples precios scraped
    
    Args:
        property_id: ID de la propiedad en OTASync
        pricing_plan_id: ID del plan de precios
        room_type_id: ID del tipo de habitación
        scraped_results: Lista de {'date': 'YYYY-MM-DD', 'price': float}
        margin_percent: Porcentaje de margen a aplicar
        
    Returns:
        dict: Resultado de la sincronización
    """
    hotel_info = {
        'otasync_property_id': property_id,
        'otasync_pricing_plan_id': pricing_plan_id,
        'otasync_room_type_id': room_type_id,
        'price_percent': margin_percent
    }
    
    integration = OfficialScrapingIntegration()
    return integration.bulk_sync_scraped_prices(hotel_info, scraped_results)


# Crear instancia global para uso fácil
official_integration = OfficialScrapingIntegration()


if __name__ == "__main__":
    print("🧪 Probando integración oficial OTASync-Scraper")
    print("=" * 50)
    
    # Datos de prueba
    hotel_info = {
        'name': 'Hotel de Prueba',
        'otasync_property_id': 9355,
        'otasync_pricing_plan_id': 26946,
        'otasync_room_type_id': 29119,
        'price_percent': 25.0  # 25% de margen
    }
    
    # Simular resultado de scraping
    scraped_price = 2560.0
    check_in_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"🏨 Hotel: {hotel_info['name']}")
    print(f"💰 Precio scraped: ${scraped_price}")
    print(f"📅 Fecha: {check_in_date}")
    print(f"📈 Margen: {hotel_info['price_percent']}%")
    
    # Probar sincronización
    integration = OfficialScrapingIntegration()
    
    if integration.connected:
        print(f"\n🔄 Sincronizando precio...")
        success = integration.sync_scraped_price(hotel_info, scraped_price, check_in_date)
        
        if success:
            print(f"✅ Sincronización exitosa")
            
            # Verificar precio
            print(f"🔍 Verificando precio...")
            expected_price = scraped_price * (1 + hotel_info['price_percent'] / 100)
            verified = integration.verify_price_sync(hotel_info, expected_price, check_in_date)
            
            if verified:
                print(f"✅ Precio verificado correctamente")
            else:
                print(f"❌ Error en verificación")
        else:
            print(f"❌ Error en sincronización")
    else:
        print(f"❌ No se pudo conectar con OTASync")
