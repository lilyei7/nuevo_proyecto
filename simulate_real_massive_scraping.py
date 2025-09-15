#!/usr/bin/env python3
"""
SIMULACIÓN DE SCRAPING MASIVO REAL
=================================

Este script simula un scraping masivo real usando:
- URLs reales de hoteles desde la base de datos
- Porcentajes de margen reales configurados 
- Integración completa con OTASync
- Fechas de 20 días automáticas
- Logging en tiempo real

Flujo completo:
1. Obtener hoteles reales con OTASync habilitado
2. Generar fechas de check-in/check-out para 20 días
3. Scraping real de Booking.com
4. Aplicar porcentajes de margen reales
5. Sincronizar precios con OTASync
6. Verificar resultados
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta
import logging
import time
import json
from typing import List, Dict, Tuple, Optional

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from intelligent_scraper import IntelligentScraper
    from otasync_api_client_official import OTASyncAPIClient
    from scraper.db import connect as db_connect
    from socket_manager import emit_log_message
    HAVE_MODULES = True
except ImportError as e:
    print(f"⚠️ Módulos requeridos no disponibles: {e}")
    HAVE_MODULES = False

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealMassiveScraper:
    """Simulador de scraping masivo real con integración OTASync"""
    
    def __init__(self, db_path: str = 'db.sqlite3'):
        """
        Inicializar el simulador de scraping masivo
        
        Args:
            db_path: Ruta a la base de datos SQLite
        """
        self.db_path = db_path
        self.scraper = None
        self.otasync_client = None
        self.results = []
        
        # Inicializar componentes si están disponibles
        if HAVE_MODULES:
            try:
                self.scraper = IntelligentScraper(headless=True)  # Ejecutar en modo headless
                self.otasync_client = OTASyncAPIClient()
                logger.info("✅ Scraper e OTASync inicializados correctamente")
            except Exception as e:
                logger.error(f"❌ Error inicializando componentes: {e}")
                self.scraper = None
                self.otasync_client = None
        
    def get_enabled_hotels(self) -> List[Dict]:
        """
        Obtener hoteles con OTASync habilitado desde la base de datos
        
        Returns:
            Lista de hoteles con configuración OTASync
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, url, price_percent, 
                       otasync_property_id, otasync_room_type_id,
                       city, country
                FROM hotels 
                WHERE otasync_enabled = 1 
                AND url IS NOT NULL 
                AND url != ''
                ORDER BY id
            """)
            
            hotels = []
            for row in cursor.fetchall():
                hotels.append({
                    'id': row['id'],
                    'name': row['name'],
                    'url': row['url'],
                    'price_percent': row['price_percent'],
                    'otasync_property_id': row['otasync_property_id'],
                    'otasync_room_type_id': row['otasync_room_type_id'],
                    'city': row['city'],
                    'country': row['country']
                })
            
            conn.close()
            
            logger.info(f"✅ Encontrados {len(hotels)} hoteles con OTASync habilitado")
            return hotels
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo hoteles: {e}")
            return []
    
    def generate_date_ranges(self, days: int = 20) -> List[Tuple[str, str]]:
        """
        Generar rangos de fechas para scraping
        
        Args:
            days: Número de días a generar
            
        Returns:
            Lista de tuplas (check_in, check_out)
        """
        date_ranges = []
        base_date = datetime.now() + timedelta(days=30)  # Empezar en 30 días
        
        for i in range(days):
            check_in = base_date + timedelta(days=i)
            check_out = check_in + timedelta(days=2)  # Estancia de 2 noches
            
            date_ranges.append((
                check_in.strftime('%Y-%m-%d'),
                check_out.strftime('%Y-%m-%d')
            ))
        
        return date_ranges
    
    def apply_margin_percentage(self, original_price: float, percentage: float) -> float:
        """
        Aplicar porcentaje de margen al precio original
        
        Args:
            original_price: Precio original scrapeado
            percentage: Porcentaje de margen a aplicar
            
        Returns:
            Precio con margen aplicado
        """
        if percentage <= 0:
            return original_price
        
        # El porcentaje puede ser 100% = doblar precio, 50% = 1.5x precio
        margin_multiplier = 1 + (percentage / 100)
        final_price = original_price * margin_multiplier
        
        return round(final_price, 2)
    
    def scrape_hotel_real(self, hotel: Dict, check_in: str, check_out: str) -> Optional[Dict]:
        """
        Scraping real de un hotel específico
        
        Args:
            hotel: Información del hotel
            check_in: Fecha de check-in (YYYY-MM-DD)
            check_out: Fecha de check-out (YYYY-MM-DD)
            
        Returns:
            Resultado del scraping con precio y disponibilidad
        """
        if not self.scraper:
            logger.warning("⚠️ Scraper no disponible - simulando...")
            # Simular precio para demostración
            import random
            simulated_price = round(random.uniform(80, 300), 2)
            return {
                'hotel_name': hotel['name'],
                'check_in': check_in,
                'check_out': check_out,
                'original_price': simulated_price,
                'currency': 'EUR',
                'availability': 'disponible',
                'simulated': True
            }
        
        try:
            logger.info(f"🔍 Scraping real: {hotel['name']} ({check_in} - {check_out})")
            
            # Usar IntelligentScraper para scraping real
            result = self.scraper.scrape_hotel_intelligent(
                hotel_url=hotel['url'],
                checkin_date=check_in,
                checkout_date=check_out,
                max_retries=3
            )
            
            if result and result.get('price_amount'):
                return {
                    'hotel_name': hotel['name'],
                    'check_in': check_in,
                    'check_out': check_out,
                    'original_price': float(result['price_amount']),
                    'currency': result.get('price_currency', 'EUR'),
                    'availability': result.get('availability', 'disponible'),
                    'simulated': False,
                    'source_url': hotel['url']
                }
            else:
                logger.warning(f"⚠️ No se obtuvo precio para {hotel['name']}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error scrapeando {hotel['name']}: {e}")
            return None
    
    def sync_price_to_otasync(self, hotel: Dict, scrape_result: Dict) -> Optional[Dict]:
        """
        Sincronizar precio con OTASync aplicando margen
        
        Args:
            hotel: Información del hotel
            scrape_result: Resultado del scraping
            
        Returns:
            Resultado de la sincronización OTASync
        """
        if not self.otasync_client:
            logger.warning("⚠️ Cliente OTASync no disponible")
            return None
        
        try:
            # Aplicar margen al precio original
            original_price = scrape_result['original_price']
            margin_percentage = hotel['price_percent']
            final_price = self.apply_margin_percentage(original_price, margin_percentage)
            
            logger.info(f"💰 Precio original: {original_price} → Con margen {margin_percentage}%: {final_price}")
            
            # Crear datos para OTASync
            otasync_data = {
                'property_id': hotel['otasync_property_id'],
                'room_type_id': hotel['otasync_room_type_id'],
                'date_from': scrape_result['check_in'],
                'date_to': scrape_result['check_out'],
                'rate': final_price,
                'currency': scrape_result.get('currency', 'EUR'),
                'availability': 1 if scrape_result['availability'] == 'disponible' else 0
            }
            
            # Sincronizar con OTASync usando el cliente oficial
            result = self.otasync_client.edit_prices([otasync_data])
            
            if result.get('success'):
                logger.info(f"✅ Sincronización exitosa - ChangeLog ID: {result.get('changelog_id')}")
                return {
                    'success': True,
                    'changelog_id': result.get('changelog_id'),
                    'original_price': original_price,
                    'final_price': final_price,
                    'margin_applied': margin_percentage,
                    'otasync_data': otasync_data
                }
            else:
                logger.error(f"❌ Error en sincronización: {result.get('message')}")
                return {'success': False, 'error': result.get('message')}
                
        except Exception as e:
            logger.error(f"❌ Error sincronizando precio: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_massive_scraping(self, max_hotels: int = 1, max_dates: int = 20) -> Dict:
        """
        Ejecutar scraping masivo real
        
        Args:
            max_hotels: Número máximo de hoteles a procesar
            max_dates: Número máximo de fechas por hotel
            
        Returns:
            Resumen de resultados del scraping masivo
        """
        logger.info("🚀 INICIANDO SCRAPING MASIVO REAL")
        logger.info("=" * 50)
        
        start_time = time.time()
        results_summary = {
            'start_time': datetime.now().isoformat(),
            'hotels_processed': 0,
            'dates_processed': 0,
            'successful_scrapes': 0,
            'successful_syncs': 0,
            'failed_scrapes': 0,
            'failed_syncs': 0,
            'results': [],
            'total_revenue_original': 0.0,
            'total_revenue_with_margin': 0.0,
            'errors': []
        }
        
        # Obtener hoteles habilitados
        hotels = self.get_enabled_hotels()
        if not hotels:
            logger.error("❌ No se encontraron hoteles con OTASync habilitado")
            return results_summary
        
        # Limitar número de hoteles
        hotels = hotels[:max_hotels]
        logger.info(f"📊 Procesando {len(hotels)} hoteles")
        
        # Generar fechas
        date_ranges = self.generate_date_ranges(max_dates)
        logger.info(f"📅 Generadas {len(date_ranges)} fechas de scraping")
        
        # Procesar cada hotel
        for hotel_idx, hotel in enumerate(hotels, 1):
            logger.info(f"\n🏨 HOTEL {hotel_idx}/{len(hotels)}: {hotel['name']}")
            logger.info(f"   URL: {hotel['url']}")
            logger.info(f"   Margen: {hotel['price_percent']}%")
            logger.info(f"   OTASync: {hotel['otasync_property_id']}/{hotel['otasync_room_type_id']}")
            
            hotel_results = []
            results_summary['hotels_processed'] += 1
            
            # Procesar fechas para este hotel
            for date_idx, (check_in, check_out) in enumerate(date_ranges, 1):
                logger.info(f"\n  📅 Fecha {date_idx}/{len(date_ranges)}: {check_in} - {check_out}")
                results_summary['dates_processed'] += 1
                
                # Scraping real
                scrape_result = self.scrape_hotel_real(hotel, check_in, check_out)
                
                if scrape_result:
                    results_summary['successful_scrapes'] += 1
                    results_summary['total_revenue_original'] += scrape_result['original_price']
                    
                    # Sincronizar con OTASync
                    sync_result = self.sync_price_to_otasync(hotel, scrape_result)
                    
                    if sync_result and sync_result.get('success'):
                        results_summary['successful_syncs'] += 1
                        results_summary['total_revenue_with_margin'] += sync_result['final_price']
                        
                        # Guardar resultado exitoso
                        hotel_results.append({
                            'date_range': f"{check_in} - {check_out}",
                            'scrape_result': scrape_result,
                            'sync_result': sync_result,
                            'status': 'success'
                        })
                        
                        logger.info(f"     ✅ Éxito: {scrape_result['original_price']} → {sync_result['final_price']}")
                    else:
                        results_summary['failed_syncs'] += 1
                        error_msg = sync_result.get('error', 'Error desconocido') if sync_result else 'Sin respuesta'
                        results_summary['errors'].append(f"Sync error - {hotel['name']} {check_in}: {error_msg}")
                        
                        hotel_results.append({
                            'date_range': f"{check_in} - {check_out}",
                            'scrape_result': scrape_result,
                            'sync_result': sync_result,
                            'status': 'sync_failed'
                        })
                        
                        logger.error(f"     ❌ Error sync: {error_msg}")
                else:
                    results_summary['failed_scrapes'] += 1
                    error_msg = f"No se obtuvo precio para {hotel['name']} {check_in}"
                    results_summary['errors'].append(error_msg)
                    
                    hotel_results.append({
                        'date_range': f"{check_in} - {check_out}",
                        'scrape_result': None,
                        'sync_result': None,
                        'status': 'scrape_failed'
                    })
                    
                    logger.error(f"     ❌ Error scrape")
                
                # Pausa entre requests para evitar rate limiting
                time.sleep(2)
            
            # Guardar resultados del hotel
            results_summary['results'].append({
                'hotel': hotel,
                'results': hotel_results
            })
            
            # Pausa entre hoteles
            time.sleep(5)
        
        # Calcular estadísticas finales
        elapsed_time = time.time() - start_time
        results_summary['end_time'] = datetime.now().isoformat()
        results_summary['elapsed_time_seconds'] = round(elapsed_time, 2)
        results_summary['success_rate_scraping'] = round(
            (results_summary['successful_scrapes'] / results_summary['dates_processed'] * 100) if results_summary['dates_processed'] > 0 else 0, 2
        )
        results_summary['success_rate_sync'] = round(
            (results_summary['successful_syncs'] / results_summary['successful_scrapes'] * 100) if results_summary['successful_scrapes'] > 0 else 0, 2
        )
        results_summary['total_margin_earned'] = round(
            results_summary['total_revenue_with_margin'] - results_summary['total_revenue_original'], 2
        )
        
        return results_summary
    
    def print_summary(self, results: Dict):
        """Imprimir resumen de resultados"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 RESUMEN DE SCRAPING MASIVO REAL")
        logger.info("=" * 60)
        logger.info(f"⏱️  Tiempo total: {results['elapsed_time_seconds']} segundos")
        logger.info(f"🏨 Hoteles procesados: {results['hotels_processed']}")
        logger.info(f"📅 Fechas procesadas: {results['dates_processed']}")
        logger.info(f"✅ Scrapes exitosos: {results['successful_scrapes']} ({results['success_rate_scraping']}%)")
        logger.info(f"🔄 Syncs exitosos: {results['successful_syncs']} ({results['success_rate_sync']}%)")
        logger.info(f"❌ Scrapes fallidos: {results['failed_scrapes']}")
        logger.info(f"❌ Syncs fallidos: {results['failed_syncs']}")
        logger.info(f"💰 Ingresos originales: €{results['total_revenue_original']:.2f}")
        logger.info(f"💰 Ingresos con margen: €{results['total_revenue_with_margin']:.2f}")
        logger.info(f"📈 Margen total ganado: €{results['total_margin_earned']:.2f}")
        
        if results['errors']:
            logger.info(f"\n⚠️  Errores encontrados ({len(results['errors'])}):")
            for error in results['errors'][:5]:  # Mostrar solo los primeros 5
                logger.info(f"   - {error}")
            if len(results['errors']) > 5:
                logger.info(f"   ... y {len(results['errors']) - 5} errores más")
    
    def save_results(self, results: Dict, filename: str = None):
        """Guardar resultados en archivo JSON"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'massive_scraping_results_{timestamp}.json'
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Resultados guardados en: {filename}")
        except Exception as e:
            logger.error(f"❌ Error guardando resultados: {e}")
    
    def cleanup(self):
        """Limpiar recursos"""
        if self.scraper:
            try:
                self.scraper.close()
                logger.info("🧹 Scraper cerrado correctamente")
            except:
                pass


def main():
    """Función principal para ejecutar scraping masivo real"""
    print("🚀 SIMULADOR DE SCRAPING MASIVO REAL")
    print("=" * 50)
    print("Este script ejecutará scraping real de hoteles con:")
    print("- URLs reales de Booking.com desde la base de datos")
    print("- Porcentajes de margen reales configurados")
    print("- Sincronización automática con OTASync")
    print("- Procesamiento de 20 fechas por hotel")
    print()
    
    # Confirmar ejecución
    response = input("¿Proceder con scraping masivo REAL? (s/N): ").strip().lower()
    if response != 's':
        print("❌ Operación cancelada")
        return
    
    # Configuración
    MAX_HOTELS = 1  # Procesar 1 hotel para demostración
    MAX_DATES = 20  # 20 fechas por hotel
    
    # Inicializar simulador
    scraper = RealMassiveScraper()
    
    try:
        # Ejecutar scraping masivo
        results = scraper.run_massive_scraping(
            max_hotels=MAX_HOTELS,
            max_dates=MAX_DATES
        )
        
        # Mostrar resumen
        scraper.print_summary(results)
        
        # Guardar resultados
        scraper.save_results(results)
        
        print("\n✅ SCRAPING MASIVO COMPLETADO")
        
    except KeyboardInterrupt:
        print("\n🛑 Scraping interrumpido por usuario")
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        logger.error(f"Error crítico en scraping masivo: {e}", exc_info=True)
    finally:
        scraper.cleanup()


if __name__ == "__main__":
    main()
