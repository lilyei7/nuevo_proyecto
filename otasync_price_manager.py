#!/usr/bin/env python3
"""
OTASync Price Manager - Gestión de Precios
Implementa los endpoints oficiales de precios de OTASync:
- POST /api/prices/data/prices - Obtener precios
- POST /api/prices/edit/prices - Actualizar precios
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os

class OTASyncPriceManager:
    """Gestor de precios para OTASync API"""
    
    def __init__(self):
        """Inicializar gestor de precios"""
        self.base_url = "https://app.otasync.me"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'OTASync-PriceManager/1.0'
        })
        
        # Cargar credenciales desde la autenticación oficial
        self.credentials = self._load_credentials()
        self.auth_data = self._authenticate()
        
        print(f"✅ OTASync Price Manager iniciado")
        print(f"📊 Usuario: {self.credentials.get('username', 'N/A')}")
    
    def _load_credentials(self):
        """Cargar credenciales desde el archivo kunas/credentials.txt"""
        try:
            credentials_file = "/home/gordon/Escritorio/scraping/nuevo_proyecto/kunas/credentials.txt"
            credentials = {}
            
            with open(credentials_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        credentials[key.strip()] = value.strip()
            
            print(f"✅ Credenciales cargadas desde: {credentials_file}")
            return credentials
            
        except Exception as e:
            print(f"❌ Error cargando credenciales: {e}")
            return {}
    
    def _authenticate(self):
        """Autenticación oficial usando /api/user/auth/login"""
        try:
            endpoint = f"{self.base_url}/api/user/auth/login"
            
            # Datos de autenticación según formato que funciona
            auth_payload = {
                "token": self.credentials.get('token'),
                "username": self.credentials.get('username'),
                "password": self.credentials.get('password'),
                "device-id": "python-client-2024"  # Device ID requerido
            }
            
            print(f"🔐 Autenticando en: {endpoint}")
            print(f"👤 Usuario: {auth_payload['username']}")
            print(f"🔑 Token: {auth_payload['token'][:20]}...")
            
            response = self.session.post(endpoint, json=auth_payload)
            
            print(f"📡 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    auth_data = response.json()
                    print(f"✅ Autenticación exitosa")
                    print(f"🔑 pkey obtenido: {auth_data.get('pkey', 'N/A')[:20]}...")
                    
                    # Agregar el token original para uso posterior
                    auth_data['token'] = self.credentials.get('token')
                    
                    if 'properties' in auth_data:
                        properties = auth_data['properties']
                        print(f"🏨 Propiedades disponibles: {len(properties)}")
                        for prop in properties:
                            print(f"   - {prop.get('name')}: ID {prop.get('id_properties')}")
                    
                    return auth_data
                except json.JSONDecodeError:
                    print(f"❌ Respuesta no es JSON válido")
                    print(f"📄 Respuesta: {response.text[:200]}...")
                    return None
            else:
                print(f"❌ Error de autenticación: {response.status_code}")
                print(f"📄 Respuesta: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error en autenticación: {e}")
            return None
    
    def get_prices(self, property_id: int, pricing_plan_id: int, date_from: str, date_to: str):
        """
        Obtener precios usando /api/prices/data/prices
        
        Args:
            property_id: ID de la propiedad
            pricing_plan_id: ID del plan de precios
            date_from: Fecha inicial (YYYY-MM-DD)
            date_to: Fecha final (YYYY-MM-DD)
        """
        try:
            if not self.auth_data:
                print("❌ No hay datos de autenticación")
                return None
            
            endpoint = f"{self.base_url}/api/prices/data/prices"
            
            payload = {
                "token": self.auth_data.get('token', ''),
                "key": self.auth_data.get('pkey', ''),
                "id_properties": property_id,
                "id_pricing_plans": pricing_plan_id,
                "dfrom": date_from,
                "dto": date_to
            }
            
            print(f"📊 Obteniendo precios para propiedad {property_id}")
            print(f"📅 Periodo: {date_from} a {date_to}")
            
            response = self.session.post(endpoint, json=payload)
            
            print(f"📡 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Precios obtenidos exitosamente")
                
                if data.get('status') == 'ok':
                    return data.get('data', {})
                else:
                    print(f"❌ Error en respuesta: {data}")
                    return None
            else:
                print(f"❌ Error obteniendo precios: {response.status_code}")
                print(f"📄 Respuesta: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error en get_prices: {e}")
            return None
    
    def edit_prices(self, property_id: int, pricing_plan_id: int, date_from: str, date_to: str, 
                   rooms: List[Dict], variation_type: int = 0, weekdays: List[int] = None):
        """
        Actualizar precios usando /api/prices/edit/prices
        
        Args:
            property_id: ID de la propiedad
            pricing_plan_id: ID del plan de precios
            date_from: Fecha inicial (YYYY-MM-DD)
            date_to: Fecha final (YYYY-MM-DD)
            rooms: Lista de habitaciones con formato [{"id_room_types": int, "value": float}]
            variation_type: Tipo de variación (-2, -1, 0, 1, 2)
                -2: Decreases price by the sent value
                -1: Decreases price by percentage
                0: Sets the price to the sent value (RECOMENDADO)
                1: Increases price by percentage
                2: Increases price by the sent value
            weekdays: Lista de 7 valores (1 o 0) para días de semana (desde Domingo)
        """
        try:
            if not self.auth_data:
                print("❌ No hay datos de autenticación")
                return False
            
            endpoint = f"{self.base_url}/api/prices/edit/prices"
            
            # Weekdays por defecto: todos los días
            if weekdays is None:
                weekdays = [1, 1, 1, 1, 1, 1, 1]  # Dom, Lun, Mar, Mie, Jue, Vie, Sab
            
            payload = {
                "token": self.auth_data.get('token', ''),
                "key": self.auth_data.get('pkey', ''),
                "id_properties": property_id,
                "id_pricing_plans": pricing_plan_id,
                "dfrom": date_from,
                "dto": date_to,
                "rooms": rooms,
                "variation_type": variation_type,
                "weekdays": weekdays
            }
            
            print(f"💰 Actualizando precios para propiedad {property_id}")
            print(f"📅 Periodo: {date_from} a {date_to}")
            print(f"🏠 Habitaciones a actualizar: {len(rooms)}")
            print(f"🔧 Tipo de variación: {variation_type} (0=fijar precio)")
            
            response = self.session.post(endpoint, json=payload)
            
            print(f"📡 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ Precios actualizados exitosamente")
                try:
                    data = response.json()
                    print(f"📄 Respuesta: {data}")
                except:
                    print(f"📄 Respuesta: {response.text}")
                return True
            else:
                print(f"❌ Error actualizando precios: {response.status_code}")
                print(f"📄 Respuesta: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error en edit_prices: {e}")
            return False
    
    def set_price_for_all_rooms(self, property_id: int, pricing_plan_id: int, 
                               price: float, date_from: str = None, date_to: str = None, 
                               days: int = 20):
        """
        Establecer un precio específico para todas las habitaciones de una propiedad
        
        Args:
            property_id: ID de la propiedad
            pricing_plan_id: ID del plan de precios
            price: Precio a establecer (ej: 3200)
            date_from: Fecha inicial (si no se especifica, usa hoy)
            date_to: Fecha final (si no se especifica, usa hoy + days)
            days: Número de días a partir de hoy (por defecto 20)
        """
        try:
            # Calcular fechas si no se especifican
            if not date_from:
                date_from = datetime.now().strftime('%Y-%m-%d')
            
            if not date_to:
                end_date = datetime.now() + timedelta(days=days)
                date_to = end_date.strftime('%Y-%m-%d')
            
            print(f"🎯 Configurando precio de ${price} para todas las habitaciones")
            print(f"📅 Periodo: {date_from} a {date_to}")
            
            # Primero obtener los precios actuales para conocer las habitaciones
            current_prices = self.get_prices(property_id, pricing_plan_id, date_from, date_to)
            
            if not current_prices:
                print("❌ No se pudieron obtener los precios actuales")
                return False
            
            # Crear lista de habitaciones con el nuevo precio
            rooms = []
            for room_id in current_prices.keys():
                rooms.append({
                    "id_room_types": int(room_id),
                    "value": price
                })
            
            print(f"🏠 Se actualizarán {len(rooms)} tipos de habitación")
            
            # Actualizar precios (variation_type=0 para fijar el precio exacto)
            success = self.edit_prices(
                property_id=property_id,
                pricing_plan_id=pricing_plan_id,
                date_from=date_from,
                date_to=date_to,
                rooms=rooms,
                variation_type=0  # Fijar precio exacto
            )
            
            if success:
                print(f"✅ Precios actualizados a ${price} para {len(rooms)} habitaciones")
                return True
            else:
                print(f"❌ Error actualizando precios")
                return False
                
        except Exception as e:
            print(f"❌ Error en set_price_for_all_rooms: {e}")
            return False
    
    def display_current_prices(self, property_id: int, pricing_plan_id: int, 
                             date_from: str = None, date_to: str = None, days: int = 7):
        """
        Mostrar precios actuales de forma legible
        """
        try:
            if not date_from:
                date_from = datetime.now().strftime('%Y-%m-%d')
            
            if not date_to:
                end_date = datetime.now() + timedelta(days=days)
                date_to = end_date.strftime('%Y-%m-%d')
            
            print(f"\n📊 PRECIOS ACTUALES - Propiedad {property_id}")
            print(f"📅 Periodo: {date_from} a {date_to}")
            print("=" * 60)
            
            prices = self.get_prices(property_id, pricing_plan_id, date_from, date_to)
            
            if not prices:
                print("❌ No se pudieron obtener precios")
                return
            
            for room_id, room_prices in prices.items():
                print(f"\n🏠 Habitación ID: {room_id}")
                print("-" * 30)
                
                # Mostrar algunos precios de muestra
                sample_dates = list(room_prices.keys())[:5]
                for date in sample_dates:
                    price = room_prices[date]
                    print(f"📅 {date}: ${price}")
                
                if len(room_prices) > 5:
                    print(f"... y {len(room_prices) - 5} fechas más")
            
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ Error mostrando precios: {e}")


def main():
    """Función principal para pruebas y uso directo"""
    print("🚀 OTASync Price Manager - Prueba")
    print("=" * 50)
    
    # Crear instancia del gestor
    price_manager = OTASyncPriceManager()
    
    if not price_manager.auth_data:
        print("❌ No se pudo autenticar. Saliendo...")
        return
    
    # Configuración para la propiedad (ajustar según sea necesario)
    PROPERTY_ID = 9355  # Usar la propiedad que conocemos
    PRICING_PLAN_ID = 26946  # ID correcto obtenido del backup del calendario
    NEW_PRICE = 3200  # Precio solicitado por el usuario
    
    print(f"\n🎯 CONFIGURACIÓN:")
    print(f"🏢 Propiedad ID: {PROPERTY_ID}")
    print(f"📋 Plan de Precios ID: {PRICING_PLAN_ID}")
    print(f"💰 Nuevo Precio: ${NEW_PRICE}")
    print(f"📅 Periodo: Hoy + 20 días")
    
    # Mostrar precios actuales
    print(f"\n1️⃣ Obteniendo precios actuales...")
    price_manager.display_current_prices(PROPERTY_ID, PRICING_PLAN_ID, days=5)
    
    # Actualizar precios
    print(f"\n2️⃣ Actualizando precios a ${NEW_PRICE}...")
    success = price_manager.set_price_for_all_rooms(
        property_id=PROPERTY_ID,
        pricing_plan_id=PRICING_PLAN_ID,
        price=NEW_PRICE,
        days=20
    )
    
    if success:
        print(f"\n3️⃣ Verificando precios actualizados...")
        price_manager.display_current_prices(PROPERTY_ID, PRICING_PLAN_ID, days=5)
    
    print(f"\n✅ Proceso completado")


if __name__ == "__main__":
    main()
