#!/usr/bin/env python3
"""
DEMO COMPLETO - Integración Scraper + OTASync Funcional
=======================================================

Este script demuestra el flujo completo:
1. Simular datos scraped de un hotel
2. Aplicar márgenes/porcentajes 
3. Sincronizar con OTASync usando la API oficial
4. Verificar que los precios se actualizaron correctamente
"""

import sys
import os
from datetime import datetime, timedelta

# Añadir directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from otasync_api_client_official import OTASyncAPIClient
    from official_scraping_integration import OfficialScrapingIntegration, sync_single_scraped_price
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    sys.exit(1)


def simulate_hotel_scraping():
    """Simular resultados de scraping de un hotel"""
    print("🤖 SIMULANDO SCRAPING DE HOTEL")
    print("-" * 35)
    
    # Datos del hotel (usando los IDs reales que funcionan)
    hotel_info = {
        'name': 'Hotel Demo Booking',
        'booking_url': 'https://www.booking.com/hotel/mx/ejemplo.html',
        'otasync_property_id': 9355,        # ID real que funciona
        'otasync_pricing_plan_id': 26946,   # Plan real que funciona  
        'otasync_room_type_id': 29119,      # Room type real que funciona
        'price_percent': 25.0               # 25% de margen
    }
    
    # Simular precios scraped para varios días
    base_date = datetime.now()
    scraped_results = []
    
    base_prices = [2400, 2600, 2800, 2500, 2700, 2900, 2300]  # Precios variados
    
    for i in range(7):  # 7 días
        date = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
        scraped_price = base_prices[i]
        
        # Calcular precio con margen
        final_price = scraped_price * (1 + hotel_info['price_percent'] / 100)
        
        scraped_results.append({
            'date': date,
            'scraped_price': scraped_price,
            'final_price': final_price,
            'margin_applied': hotel_info['price_percent']
        })
    
    print(f"🏨 Hotel: {hotel_info['name']}")
    print(f"🔗 URL: {hotel_info['booking_url']}")
    print(f"🏢 OTASync Property ID: {hotel_info['otasync_property_id']}")
    print(f"🏠 Room Type ID: {hotel_info['otasync_room_type_id']}")
    print(f"📈 Margen configurado: {hotel_info['price_percent']}%")
    print(f"\n📊 PRECIOS SCRAPED:")
    
    for result in scraped_results:
        print(f"  📅 {result['date']}: ${result['scraped_price']:,.2f} → ${result['final_price']:,.2f} (+{result['margin_applied']}%)")
    
    return hotel_info, scraped_results


def sync_with_otasync(hotel_info, scraped_results):
    """Sincronizar precios scraped con OTASync"""
    print(f"\n🔄 SINCRONIZACIÓN CON OTASYNC")
    print("-" * 35)
    
    # Crear cliente OTASync
    client = OTASyncAPIClient()
    
    if not client.token or not client.key:
        print("❌ No se pudieron cargar las credenciales")
        return False
    
    print(f"✅ Cliente OTASync conectado")
    print(f"🔑 Token: {client.token[:20]}...")
    print(f"🔑 Key: {client.key[:20]}...")
    
    # Mostrar precios actuales antes de la actualización
    print(f"\n📋 PRECIOS ACTUALES EN OTASYNC:")
    current_prices = client.get_prices(
        property_id=hotel_info['otasync_property_id'],
        pricing_plan_id=hotel_info['otasync_pricing_plan_id'],
        date_from=scraped_results[0]['date'],
        date_to=scraped_results[-1]['date']
    )
    
    room_type_str = str(hotel_info['otasync_room_type_id'])
    if current_prices and room_type_str in current_prices:
        for date in [r['date'] for r in scraped_results]:
            current_price = current_prices[room_type_str].get(date, 'N/A')
            print(f"  📅 {date}: ${current_price}")
    
    # Sincronizar cada precio
    print(f"\n💰 ACTUALIZANDO PRECIOS:")
    success_count = 0
    
    for result in scraped_results:
        print(f"  🔄 {result['date']}: ${result['final_price']:,.2f}")
        
        success = client.update_single_room_price(
            property_id=hotel_info['otasync_property_id'],
            pricing_plan_id=hotel_info['otasync_pricing_plan_id'],
            room_type_id=hotel_info['otasync_room_type_id'],
            price=result['final_price'],
            date_from=result['date'],
            date_to=result['date']
        )
        
        if success:
            success_count += 1
            print(f"    ✅ Actualizado exitosamente")
        else:
            print(f"    ❌ Error en actualización")
    
    print(f"\n📊 RESULTADO: {success_count}/{len(scraped_results)} precios actualizados")
    
    return success_count > 0


def verify_sync(hotel_info, scraped_results):
    """Verificar que los precios se sincronizaron correctamente"""
    print(f"\n🔍 VERIFICACIÓN DE SINCRONIZACIÓN")
    print("-" * 35)
    
    client = OTASyncAPIClient()
    
    # Obtener precios actuales después de la actualización
    updated_prices = client.get_prices(
        property_id=hotel_info['otasync_property_id'],
        pricing_plan_id=hotel_info['otasync_pricing_plan_id'],
        date_from=scraped_results[0]['date'],
        date_to=scraped_results[-1]['date']
    )
    
    if not updated_prices:
        print("❌ No se pudieron obtener precios para verificación")
        return False
    
    room_type_str = str(hotel_info['otasync_room_type_id'])
    verified_count = 0
    
    print(f"📋 VERIFICANDO PRECIOS ACTUALIZADOS:")
    
    for result in scraped_results:
        expected_price = result['final_price']
        actual_price = None
        
        if room_type_str in updated_prices and result['date'] in updated_prices[room_type_str]:
            actual_price = float(updated_prices[room_type_str][result['date']])
            
            # Permitir pequeña diferencia por redondeo
            price_diff = abs(actual_price - expected_price)
            
            if price_diff < 0.01:
                print(f"  ✅ {result['date']}: ${actual_price:,.2f} (esperado ${expected_price:,.2f})")
                verified_count += 1
            else:
                print(f"  ❌ {result['date']}: ${actual_price:,.2f} (esperado ${expected_price:,.2f}) - Diferencia: ${price_diff:,.2f}")
        else:
            print(f"  ❌ {result['date']}: No encontrado en OTASync")
    
    print(f"\n📊 VERIFICACIÓN: {verified_count}/{len(scraped_results)} precios correctos")
    
    return verified_count == len(scraped_results)


def main():
    """Ejecutar demo completo"""
    print("🚀 DEMO COMPLETO - INTEGRACIÓN SCRAPER + OTASYNC")
    print("=" * 60)
    
    try:
        # 1. Simular scraping
        hotel_info, scraped_results = simulate_hotel_scraping()
        
        # 2. Sincronizar con OTASync
        sync_success = sync_with_otasync(hotel_info, scraped_results)
        
        if not sync_success:
            print("❌ Falló la sincronización con OTASync")
            return False
        
        # 3. Verificar sincronización
        verify_success = verify_sync(hotel_info, scraped_results)
        
        # 4. Resumen final
        print(f"\n{'=' * 60}")
        print("🏁 RESUMEN DEL DEMO")
        print(f"{'=' * 60}")
        
        print(f"🏨 Hotel procesado: {hotel_info['name']}")
        print(f"📊 Precios procesados: {len(scraped_results)}")
        print(f"📈 Margen aplicado: {hotel_info['price_percent']}%")
        print(f"🔄 Sincronización: {'✅ Exitosa' if sync_success else '❌ Fallida'}")
        print(f"🔍 Verificación: {'✅ Correcta' if verify_success else '❌ Incorrecta'}")
        
        if sync_success and verify_success:
            print(f"\n🎉 ¡DEMO COMPLETADO EXITOSAMENTE!")
            print(f"✅ El sistema de integración Scraper + OTASync está funcionando correctamente")
            print(f"✅ Los precios scraped se están sincronizando con márgenes aplicados")
            print(f"✅ La verificación confirma que los precios se actualizaron correctamente")
        else:
            print(f"\n⚠️ DEMO COMPLETADO CON PROBLEMAS")
            print(f"❌ Revisa los errores anteriores para identificar el problema")
        
        return sync_success and verify_success
        
    except Exception as e:
        print(f"💥 Error en el demo: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
