#!/usr/bin/env python3
"""
Configurar hotel PARK INN MAZATLAN para testing
"""

import os
import sys
import logging

# Agregar el directorio actual al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.db import DatabaseManager

def setup_hotel():
    """Configurar hotel de prueba"""
    print("🏨 Configurando hotel PARK INN MAZATLAN...")
    print("-" * 50)
    
    # Crear instancia de base de datos
    db = DatabaseManager()
    
    # Insertar hotel
    hotel_id = db.insert_hotel(
        name="PARK INN MAZATLAN",
        url="https://www.booking.com/hotel/mx/park-inn-by-radisson-mazatlan.html",
        city="Mazatlán",
        country="México"
    )
    
    print(f"✅ Hotel insertado con ID: {hotel_id}")
    
    # Configurar información de OTASync - Asegurarse de que el margen de precio se aplica
    db.update_hotel_otasync_info(
        hotel_id=hotel_id,
        property_id="9355",
        room_type_id="1001",
        enabled=True,
        price_percent=25.0  # Configura un 25% de margen
    )
    
    print(f"✅ Información OTASync configurada:")
    print(f"   - Property ID: 9355")
    print(f"   - Room Type ID: 1001")
    print(f"   - Enabled: True")
    print(f"   - Margen de precio: 25.0%")
    
    # Verificar configuración
    hotels = db.get_hotels_with_otasync_enabled()
    print(f"\n📊 Hoteles con OTASync habilitado: {len(hotels)}")
    
    for hotel in hotels:
        print(f"   - {hotel['name']} (ID: {hotel['id']})")
        print(f"     Property ID: {hotel['otasync_property_id']}")
        print(f"     Room Type ID: {hotel['otasync_room_type_id']}")
    
    # DatabaseManager no tiene método close()
    print(f"\n✅ Configuración completada exitosamente")

if __name__ == "__main__":
    setup_hotel()
