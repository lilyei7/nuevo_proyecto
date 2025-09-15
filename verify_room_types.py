#!/usr/bin/env python3
"""
VERIFICAR ROOM TYPES DE PROPIEDAD 9355
=====================================

Este script verifica qué room types están disponibles para la propiedad 9355
y cuáles son los precios actuales para cada room type.
"""

import sys
import os

# Agregar el directorio del proyecto al path
sys.path.append('/home/gordon/Escritorio/scraping/nuevo_proyecto')

from otasync_api_client_official import OTASyncAPI
from datetime import date, timedelta

def verify_room_types():
    """Verificar room types disponibles para la propiedad 9355"""
    
    print("🔍 VERIFICANDO ROOM TYPES PARA PROPIEDAD 9355")
    print("=" * 50)
    
    # Inicializar cliente OTASync
    client = OTASyncAPI()
    
    # Fecha actual
    today = date.today()
    date_str = today.strftime('%Y-%m-%d')
    
    print(f"📅 Consultando precios para fecha: {date_str}")
    print()
    
    try:
        # Obtener precios para la propiedad 9355
        prices = client.get_prices_for_date(
            property_id=9355,
            date=date_str
        )
        
        if prices:
            print(f"✅ Encontrados precios para {len(prices)} room types:")
            print()
            
            for room_id, price_data in prices.items():
                print(f"🏠 Room Type ID: {room_id}")
                print(f"   💰 Precio actual: ${price_data.get('price', 'N/A')}")
                print(f"   📊 Disponibilidad: {price_data.get('availability', 'N/A')}")
                print()
        else:
            print("❌ No se encontraron precios para esta propiedad")
            
    except Exception as e:
        print(f"❌ Error al obtener precios: {e}")
    
    print("\n" + "=" * 50)
    print("🔍 VERIFICANDO ROOM TYPE 29119 ESPECÍFICAMENTE")
    print("=" * 50)
    
    try:
        # Probar actualización de precios con room type 29119
        test_price = 1500.00
        
        print(f"🧪 Probando actualización de precio a ${test_price}")
        print(f"🏠 Room Type: 29119")
        print(f"📅 Fecha: {date_str}")
        
        rooms = [{
            "id_room_types": 29119,
            "value": test_price
        }]
        
        success = client.edit_prices(
            property_id=9355,
            pricing_plan_id=1001,  # Plan estándar
            date_from=date_str,
            date_to=date_str,
            rooms=rooms,
            variation_type=0
        )
        
        if success:
            print("✅ Actualización de prueba exitosa")
        else:
            print("❌ Falló la actualización de prueba")
            
    except Exception as e:
        print(f"❌ Error en actualización de prueba: {e}")

if __name__ == "__main__":
    verify_room_types()
