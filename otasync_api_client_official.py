#!/usr/bin/env python3
"""
Cliente OTASync Oficial - Implementación correcta de la API
===========================================================

Este cliente implementa correctamente los endpoints oficiales de OTASync:
- POST /api/prices/data/prices - Obtener precios
- POST /api/prices/edit/prices - Actualizar precios

Usa las credenciales correctas desde credentials.txt y maneja la autenticación apropiadamente.
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

class OTASyncAPIClient:
    """Cliente oficial para la API de OTASync"""
    
    def __init__(self):
        """Inicializar cliente con credenciales correctas"""
        self.base_url = "https://app.otasync.me"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'OTASync-Official-Client/1.0'
        })
        
        # Cargar credenciales desde el archivo credentials.txt
        self.credentials = self._load_credentials()
        self.token = self.credentials.get('token')
        self.key = None  # Se obtiene durante la autenticación
        
        print(f"✅ OTASync API Client iniciado")
        print(f"🔑 Token: {self.token[:20] if self.token else 'No encontrado'}...")
        print(f"👤 Usuario: {self.credentials.get('username', 'N/A')}")
        
        # Intentar obtener el key mediante autenticación
        self._authenticate()
    
    def _load_credentials(self):
        """Cargar credenciales desde kunas/credentials.txt"""
        try:
            # Buscar el archivo credentials.txt
            possible_paths = [
                "/home/gordon/Escritorio/scraping/nuevo_proyecto/kunas/credentials.txt",
                "/home/gordon/Escritorio/scraping/kunas/credentials.txt",
                os.path.join(os.path.dirname(__file__), "kunas", "credentials.txt"),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "kunas", "credentials.txt")
            ]
            
            credentials = {}
            credentials_file = None
            
            for path in possible_paths:
                if os.path.exists(path):
                    credentials_file = path
                    break
            
            if not credentials_file:
                print(f"❌ No se encontró credentials.txt en ninguna ubicación")
                return {}
            
            print(f"📁 Cargando credenciales desde: {credentials_file}")
            
            with open(credentials_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        credentials[key.strip()] = value.strip()
            
            print(f"✅ Credenciales cargadas exitosamente")
            return credentials
            
        except Exception as e:
            print(f"❌ Error cargando credenciales: {e}")
            return {}
    
    def _authenticate(self):
        """Obtener el key de autenticación"""
        try:
            if not self.token:
                print("❌ No hay token disponible para autenticación")
                return False
            
            # Para OTASync, el key se puede obtener mediante login o usar el token directamente
            # Según la documentación, necesitamos tanto token como key
            
            # Intentar login para obtener el key
            login_endpoint = f"{self.base_url}/api/user/auth/login"
            login_payload = {
                "token": self.token,
                "username": self.credentials.get('username'),
                "password": self.credentials.get('password'),
                "device-id": "otasync-api-client-2024"
            }
            
            print(f"🔐 Autenticando con OTASync...")
            response = self.session.post(login_endpoint, json=login_payload, timeout=30)
            
            if response.status_code == 200:
                auth_data = response.json()
                print(f"✅ Autenticación exitosa")
                
                # Extraer pkey que es el key real según la respuesta
                if 'pkey' in auth_data:
                    self.key = auth_data['pkey']
                    print(f"🔑 pkey obtenido: {self.key[:20]}...")
                elif 'key' in auth_data:
                    self.key = auth_data['key']
                    print(f"🔑 key obtenido: {self.key[:20]}...")
                elif 'data' in auth_data and isinstance(auth_data['data'], dict):
                    if 'pkey' in auth_data['data']:
                        self.key = auth_data['data']['pkey']
                        print(f"🔑 pkey de data obtenido: {self.key[:20]}...")
                    elif 'key' in auth_data['data']:
                        self.key = auth_data['data']['key']
                        print(f"🔑 key de data obtenido: {self.key[:20]}...")
                    else:
                        self.key = self.token
                        print(f"🔑 Usando token como key (fallback)")
                else:
                    self.key = self.token
                    print(f"🔑 Usando token como key (no encontrado)")
                
                return True
            else:
                print(f"❌ Error en autenticación: {response.status_code}")
                print(f"Respuesta: {response.text}")
                # Usar token como key por defecto
                self.key = self.token
                return False
                
        except Exception as e:
            print(f"❌ Error en autenticación: {e}")
            # Usar token como key por defecto
            self.key = self.token
            return False
    
    def get_prices(self, property_id: int, pricing_plan_id: int, date_from: str, date_to: str) -> Dict[str, Any]:
        """
        Obtener precios usando la API oficial /api/prices/data/prices
        
        Args:
            property_id: ID de la propiedad
            pricing_plan_id: ID del plan de precios
            date_from: Fecha inicial (YYYY-MM-DD)
            date_to: Fecha final (YYYY-MM-DD)
            
        Returns:
            Dict con los precios en formato: {'room_type_id': {'date': price}}
        """
        try:
            endpoint = f"{self.base_url}/api/prices/data/prices"
            
            payload = {
                "token": self.token,
                "key": self.key,
                "id_properties": int(property_id),
                "id_pricing_plans": int(pricing_plan_id),
                "dfrom": date_from,
                "dto": date_to
            }
            
            print(f"📊 Obteniendo precios para propiedad {property_id}")
            print(f"📅 Periodo: {date_from} a {date_to}")
            
            response = self.session.post(endpoint, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok' and 'data' in data:
                    prices = data['data']
                    print(f"✅ Precios obtenidos: {len(prices)} room types")
                    return prices
                else:
                    print(f"❌ Error en respuesta: {data}")
                    return {}
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                return {}
                
        except Exception as e:
            print(f"❌ Error obteniendo precios: {e}")
            return {}
    
    def edit_prices(self, property_id: int, pricing_plan_id: int, date_from: str, date_to: str, 
                   rooms: List[Dict[str, Any]], variation_type: int = 0, 
                   weekdays: List[int] = None) -> bool:
        """
        Actualizar precios usando la API oficial /api/prices/edit/prices
        
        Args:
            property_id: ID de la propiedad
            pricing_plan_id: ID del plan de precios
            date_from: Fecha inicial (YYYY-MM-DD)
            date_to: Fecha final (YYYY-MM-DD)
            rooms: Lista de habitaciones [{"id_room_types": int, "value": float}]
            variation_type: Tipo de variación:
                -2: Decreases price by the sent value
                -1: Decreases price by percentage
                0: Sets the price to the sent value (RECOMENDADO)
                1: Increases price by percentage
                2: Increases price by the sent value
            weekdays: Lista de 7 valores (1 o 0) para días de semana (desde Domingo)
            
        Returns:
            bool: True si la actualización fue exitosa
        """
        try:
            endpoint = f"{self.base_url}/api/prices/edit/prices"
            
            # Valores por defecto para weekdays (todos los días)
            if weekdays is None:
                weekdays = [1, 1, 1, 1, 1, 1, 1]  # Domingo a Sábado
            
            payload = {
                "token": self.token,
                "key": self.key,
                "id_properties": int(property_id),
                "id_pricing_plans": int(pricing_plan_id),
                "dfrom": date_from,
                "dto": date_to,
                "rooms": rooms,
                "variation_type": variation_type,
                "weekdays": weekdays
            }
            
            print(f"💰 Actualizando precios para propiedad {property_id}")
            print(f"📅 Periodo: {date_from} a {date_to}")
            print(f"🏠 Habitaciones: {len(rooms)}")
            print(f"🔄 Tipo de variación: {variation_type}")
            
            response = self.session.post(endpoint, json=payload, timeout=30)
            
            if response.status_code in [200, 204]:
                try:
                    data = response.json() if response.text else {"status": "ok"}
                except:
                    data = {"status": "ok"}  # Respuesta exitosa sin JSON
                
                # La respuesta de OTASync incluye información del changelog cuando es exitosa
                if data.get('status') in ['ok', 'success'] or 'id_changelog' in data or response.status_code == 204:
                    if 'id_changelog' in data:
                        print(f"✅ Precios actualizados exitosamente - Changelog ID: {data['id_changelog']}")
                        if 'old_values' in data and 'new_values' in data:
                            print(f"🔄 Cambio registrado: {data['old_values']} → {data['new_values']}")
                    else:
                        print(f"✅ Precios actualizados exitosamente")
                    return True
                else:
                    print(f"❌ Error en actualización: {data}")
                    return False
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error actualizando precios: {e}")
            return False
    
    def update_single_room_price(self, property_id: int, pricing_plan_id: int, room_type_id: int,
                               price: float, date_from: str = None, date_to: str = None) -> bool:
        """
        Actualizar precio de una habitación específica
        
        Args:
            property_id: ID de la propiedad
            pricing_plan_id: ID del plan de precios
            room_type_id: ID del tipo de habitación
            price: Precio a establecer
            date_from: Fecha inicial (por defecto hoy)
            date_to: Fecha final (por defecto hoy)
        """
        if not date_from:
            date_from = datetime.now().strftime('%Y-%m-%d')
        if not date_to:
            date_to = date_from
        
        rooms = [{
            "id_room_types": int(room_type_id),
            "value": float(price)
        }]
        
        return self.edit_prices(
            property_id=property_id,
            pricing_plan_id=pricing_plan_id,
            date_from=date_from,
            date_to=date_to,
            rooms=rooms,
            variation_type=0  # Establecer precio exacto
        )
    
    def update_bulk_prices_optimized(self, property_id: int, pricing_plan_id: int, room_type_id: int,
                                     date_prices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Actualizar múltiples precios de forma optimizada - agrupa fechas por precio
        
        Args:
            property_id: ID de la propiedad
            pricing_plan_id: ID del plan de precios
            room_type_id: ID del tipo de habitación
            date_prices: Lista de {"date": "YYYY-MM-DD", "price": float}
        """
        results = {
            'total': len(date_prices),
            'success': 0,
            'failed': 0,
            'errors': [],
            'api_calls': 0
        }
        
        if not date_prices:
            return results
        
        print(f"📦 Actualizando {len(date_prices)} precios de forma optimizada")
        
        # Agrupar fechas por precio para optimizar requests
        price_groups = {}
        for date_price in date_prices:
            price = float(date_price['price'])
            if price not in price_groups:
                price_groups[price] = []
            price_groups[price].append(date_price['date'])
        
        print(f"🔄 Agrupados en {len(price_groups)} grupos de precios")
        
        # Procesar cada grupo de precios
        for price, dates in price_groups.items():
            try:
                # Ordenar fechas para crear rangos
                dates.sort()
                date_from = dates[0]
                date_to = dates[-1]
                
                print(f"  💰 Estableciendo ${price} para {len(dates)} fechas ({date_from} a {date_to})")
                
                # Crear payload para múltiples fechas con el mismo precio
                rooms = [{
                    "id_room_types": int(room_type_id),
                    "value": float(price)
                }]
                
                success = self.edit_prices(
                    property_id=property_id,
                    pricing_plan_id=pricing_plan_id,
                    date_from=date_from,
                    date_to=date_to,
                    rooms=rooms,
                    variation_type=0  # Establecer precio exacto
                )
                
                results['api_calls'] += 1
                
                if success:
                    results['success'] += len(dates)
                    for date in dates:
                        print(f"    ✅ {date}: ${price}")
                else:
                    results['failed'] += len(dates)
                    error_msg = f"Error actualizando grupo de precio ${price}"
                    results['errors'].append(error_msg)
                    print(f"    ❌ {error_msg}")
                    
            except Exception as e:
                results['failed'] += len(dates)
                error_msg = f"Excepción en grupo ${price}: {e}"
                results['errors'].append(error_msg)
                print(f"    ❌ {error_msg}")
        
        print(f"📊 Resultado optimizado: {results['success']} éxitos, {results['failed']} fallos en {results['api_calls']} API calls")
        return results

    def update_bulk_prices(self, property_id: int, pricing_plan_id: int, room_type_id: int,
                          date_prices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Actualizar múltiples precios para una habitación en diferentes fechas
        Usa método optimizado por defecto
        
        Args:
            property_id: ID de la propiedad
            pricing_plan_id: ID del plan de precios
            room_type_id: ID del tipo de habitación
            date_prices: Lista de {"date": "YYYY-MM-DD", "price": float}
        """
        # Usar método optimizado primero
        try:
            return self.update_bulk_prices_optimized(property_id, pricing_plan_id, room_type_id, date_prices)
        except Exception as e:
            print(f"⚠️ Método optimizado falló, usando método individual: {e}")
            
            # Fallback al método individual
            results = {
                'total': len(date_prices),
                'success': 0,
                'failed': 0,
                'errors': [],
                'api_calls': 0
            }
            
            print(f"📦 Actualizando {len(date_prices)} precios individualmente")
            
            for date_price in date_prices:
                try:
                    success = self.update_single_room_price(
                        property_id=property_id,
                        pricing_plan_id=pricing_plan_id,
                        room_type_id=room_type_id,
                        price=date_price['price'],
                        date_from=date_price['date'],
                        date_to=date_price['date']
                    )
                    
                    results['api_calls'] += 1
                    
                    if success:
                        results['success'] += 1
                        print(f"  ✅ {date_price['date']}: ${date_price['price']}")
                    else:
                        results['failed'] += 1
                        error_msg = f"Error actualizando {date_price['date']}"
                        results['errors'].append(error_msg)
                        print(f"  ❌ {error_msg}")
                        
                except Exception as e:
                    results['failed'] += 1
                    results['api_calls'] += 1
                    error_msg = f"Excepción en {date_price['date']}: {e}"
                    results['errors'].append(error_msg)
                    print(f"  ❌ {error_msg}")
            
            print(f"📊 Resultado individual: {results['success']} éxitos, {results['failed']} fallos en {results['api_calls']} API calls")
            return results
    
    def display_prices(self, property_id: int, pricing_plan_id: int, 
                      date_from: str = None, date_to: str = None, days: int = 7):
        """Mostrar precios actuales de forma legible"""
        if not date_from:
            date_from = datetime.now().strftime('%Y-%m-%d')
        if not date_to:
            end_date = datetime.strptime(date_from, '%Y-%m-%d') + timedelta(days=days-1)
            date_to = end_date.strftime('%Y-%m-%d')
        
        print(f"\n📋 PRECIOS ACTUALES - Propiedad {property_id}")
        print(f"📅 Periodo: {date_from} a {date_to}")
        print("=" * 60)
        
        prices = self.get_prices(property_id, pricing_plan_id, date_from, date_to)
        
        if not prices:
            print("❌ No se pudieron obtener precios")
            return
        
        for room_type_id, dates in prices.items():
            print(f"\n🏠 Room Type ID: {room_type_id}")
            for date, price in dates.items():
                print(f"  📅 {date}: ${price}")
    
    def test_connection(self):
        """Probar la conexión con la API"""
        try:
            # Usar propiedades conocidas para prueba
            test_property_id = 9355  # La propiedad que sabemos que existe
            test_pricing_plan_id = 26946
            test_date = datetime.now().strftime('%Y-%m-%d')
            
            print(f"🧪 Probando conexión con la API...")
            prices = self.get_prices(test_property_id, test_pricing_plan_id, test_date, test_date)
            
            if prices:
                print(f"✅ Conexión exitosa - {len(prices)} room types encontrados")
                return True
            else:
                print(f"❌ Conexión fallida - No se obtuvieron precios")
                return False
                
        except Exception as e:
            print(f"❌ Error probando conexión: {e}")
            return False


def main():
    """Función principal para pruebas"""
    print("🚀 OTASync API Client - Prueba de Conexión")
    print("=" * 50)
    
    # Crear cliente
    client = OTASyncAPIClient()
    
    if not client.token:
        print("❌ No se encontraron credenciales válidas")
        return
    
    # Probar conexión
    if client.test_connection():
        print("\n🎯 Conexión establecida exitosamente")
        
        # Mostrar precios actuales
        print("\n📊 Mostrando precios actuales (5 días)...")
        client.display_prices(9355, 26946, days=5)
        
        # Ejemplo de actualización de precio
        print(f"\n💰 Ejemplo: Actualizando precio de room type 29119 a $3200")
        success = client.update_single_room_price(
            property_id=9355,
            pricing_plan_id=26946,
            room_type_id=29119,
            price=3200,
            date_from=datetime.now().strftime('%Y-%m-%d')
        )
        
        if success:
            print("✅ Precio actualizado exitosamente")
        else:
            print("❌ Error actualizando precio")
    else:
        print("❌ No se pudo establecer conexión con OTASync")


if __name__ == "__main__":
    main()
