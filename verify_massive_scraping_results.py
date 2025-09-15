#!/usr/bin/env python3
"""
VERIFICADOR DE RESULTADOS DE SCRAPING MASIVO
===========================================

Este script verifica los resultados del scraping masivo real:
- Consulta los precios actualizados en OTASync
- Verifica que las actualizaciones se aplicaron correctamente
- Genera un reporte de verificación detallado
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta
import logging
import json
from typing import List, Dict, Optional

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from otasync_api_client_official import OTASyncAPIClient
    HAVE_OTASYNC = True
except ImportError:
    HAVE_OTASYNC = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MassiveScrapingVerifier:
    """Verificador de resultados de scraping masivo"""
    
    def __init__(self, db_path: str = 'db.sqlite3'):
        self.db_path = db_path
        self.otasync_client = None
        
        if HAVE_OTASYNC:
            try:
                self.otasync_client = OTASyncAPIClient()
                logger.info("✅ Cliente OTASync inicializado")
            except Exception as e:
                logger.error(f"❌ Error inicializando OTASync: {e}")
    
    def get_enabled_hotels(self) -> List[Dict]:
        """Obtener hoteles con OTASync habilitado"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, url, price_percent, 
                       otasync_property_id, otasync_room_type_id
                FROM hotels 
                WHERE otasync_enabled = 1 
            """)
            
            hotels = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            logger.info(f"✅ Encontrados {len(hotels)} hoteles para verificar")
            return hotels
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo hoteles: {e}")
            return []
    
    def generate_verification_dates(self, days: int = 20) -> List[str]:
        """Generar fechas para verificación"""
        dates = []
        base_date = datetime.now() + timedelta(days=30)
        
        for i in range(days):
            date = base_date + timedelta(days=i)
            dates.append(date.strftime('%Y-%m-%d'))
        
        return dates
    
    def verify_otasync_prices(self, hotel: Dict, dates: List[str]) -> Dict:
        """Verificar precios en OTASync para un hotel"""
        if not self.otasync_client:
            return {'error': 'Cliente OTASync no disponible'}
        
        try:
            logger.info(f"🔍 Verificando precios para {hotel['name']}")
            
            # Consultar precios en OTASync usando la signatura correcta
            price_data = self.otasync_client.get_prices(
                property_id=int(hotel['otasync_property_id']),
                pricing_plan_id=26946,  # Plan conocido que funciona
                date_from=dates[0],
                date_to=dates[-1]
            )
            
            # El método devuelve directamente un diccionario de precios
            # Formato: {room_type_id: {date: price, ...}, ...}
            
            verification_result = {
                'success': True,
                'hotel_name': hotel['name'],
                'property_id': hotel['otasync_property_id'],
                'room_type_id': hotel['otasync_room_type_id'],
                'expected_dates': len(dates),
                'found_prices': 0,
                'prices': [],
                'coverage_percentage': 0.0,
                'date_coverage': [],
                'missing_dates': [],
                'price_analysis': {
                    'min_rate': None,
                    'max_rate': None,
                    'avg_rate': None,
                    'total_rates': 0
                }
            }
            
            # Procesar los datos de precio
            if price_data and isinstance(price_data, dict):
                room_type_id = hotel['otasync_room_type_id']
                
                # Buscar precios para este room_type_id
                room_prices = price_data.get(room_type_id, {})
                
                if room_prices:
                    prices = []
                    for date, price in room_prices.items():
                        prices.append({
                            'date': date,
                            'rate': float(price),
                            'room_type_id': room_type_id
                        })
                    
                    verification_result['found_prices'] = len(prices)
                    verification_result['prices'] = prices
                    
                    # Análizar cobertura de fechas
                    price_dates = set(room_prices.keys())
                    expected_dates = set(dates)
                    
                    verification_result['date_coverage'] = sorted(list(price_dates))
                    verification_result['missing_dates'] = sorted(list(expected_dates - price_dates))
                    verification_result['coverage_percentage'] = round(
                        (len(price_dates.intersection(expected_dates)) / len(dates)) * 100, 2
                    )
                    
                    # Análisis de precios
                    if prices:
                        rates = [p['rate'] for p in prices]
                        verification_result['price_analysis'].update({
                            'min_rate': min(rates),
                            'max_rate': max(rates),
                            'avg_rate': round(sum(rates) / len(rates), 2),
                            'total_rates': len(rates)
                        })
            
            logger.info(f"   📊 Encontrados {verification_result['found_prices']} precios de {len(dates)} fechas esperadas ({verification_result['coverage_percentage']}%)")
            
            return verification_result
            
        except Exception as e:
            logger.error(f"❌ Error verificando precios para {hotel['name']}: {e}")
            return {
                'success': False,
                'error': str(e),
                'hotel_name': hotel['name']
            }
    
    def load_scraping_results(self, results_file: str) -> Optional[Dict]:
        """Cargar resultados del scraping masivo"""
        try:
            if os.path.exists(results_file):
                with open(results_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"⚠️ No se encontró archivo de resultados: {results_file}")
                return None
        except Exception as e:
            logger.error(f"❌ Error cargando resultados: {e}")
            return None
    
    def verify_massive_scraping(self, results_file: str = None) -> Dict:
        """Verificar resultados del scraping masivo"""
        logger.info("🔍 INICIANDO VERIFICACIÓN DE SCRAPING MASIVO")
        logger.info("=" * 50)
        
        verification_summary = {
            'start_time': datetime.now().isoformat(),
            'hotels_verified': 0,
            'successful_verifications': 0,
            'failed_verifications': 0,
            'total_prices_found': 0,
            'total_dates_expected': 0,
            'overall_coverage': 0.0,
            'hotel_results': [],
            'scraping_results': None,
            'comparison': None
        }
        
        # Cargar resultados del scraping si se proporciona
        if results_file:
            scraping_results = self.load_scraping_results(results_file)
            verification_summary['scraping_results'] = scraping_results
        
        # Obtener hoteles
        hotels = self.get_enabled_hotels()
        if not hotels:
            logger.error("❌ No se encontraron hoteles para verificar")
            return verification_summary
        
        # Generar fechas
        verification_dates = self.generate_verification_dates(20)
        verification_summary['total_dates_expected'] = len(verification_dates) * len(hotels)
        
        logger.info(f"📊 Verificando {len(hotels)} hoteles para {len(verification_dates)} fechas")
        
        # Verificar cada hotel
        for hotel in hotels:
            logger.info(f"\n🏨 Verificando: {hotel['name']}")
            
            verification_result = self.verify_otasync_prices(hotel, verification_dates)
            verification_summary['hotels_verified'] += 1
            
            if verification_result.get('success'):
                verification_summary['successful_verifications'] += 1
                verification_summary['total_prices_found'] += verification_result.get('found_prices', 0)
                
                logger.info(f"   ✅ Verificación exitosa - {verification_result['coverage_percentage']}% cobertura")
            else:
                verification_summary['failed_verifications'] += 1
                logger.error(f"   ❌ Verificación fallida: {verification_result.get('error')}")
            
            verification_summary['hotel_results'].append(verification_result)
        
        # Calcular estadísticas generales
        if verification_summary['total_dates_expected'] > 0:
            verification_summary['overall_coverage'] = round(
                (verification_summary['total_prices_found'] / verification_summary['total_dates_expected']) * 100, 2
            )
        
        verification_summary['end_time'] = datetime.now().isoformat()
        
        # Comparar con resultados del scraping si están disponibles
        if verification_summary['scraping_results']:
            verification_summary['comparison'] = self.compare_with_scraping_results(
                verification_summary,
                verification_summary['scraping_results']
            )
        
        return verification_summary
    
    def compare_with_scraping_results(self, verification: Dict, scraping: Dict) -> Dict:
        """Comparar verificación con resultados del scraping"""
        try:
            comparison = {
                'scraping_success_rate': scraping.get('success_rate_sync', 0),
                'verification_coverage': verification.get('overall_coverage', 0),
                'consistency_check': 'pending',
                'scraping_syncs': scraping.get('successful_syncs', 0),
                'verification_prices': verification.get('total_prices_found', 0),
                'match_percentage': 0.0
            }
            
            # Verificar consistencia
            scraping_syncs = scraping.get('successful_syncs', 0)
            verification_prices = verification.get('total_prices_found', 0)
            
            if scraping_syncs > 0:
                match_percentage = (verification_prices / scraping_syncs) * 100
                comparison['match_percentage'] = round(match_percentage, 2)
                
                if match_percentage >= 95:
                    comparison['consistency_check'] = 'excelente'
                elif match_percentage >= 80:
                    comparison['consistency_check'] = 'buena'
                elif match_percentage >= 60:
                    comparison['consistency_check'] = 'aceptable'
                else:
                    comparison['consistency_check'] = 'problemas detectados'
            
            return comparison
            
        except Exception as e:
            logger.error(f"❌ Error en comparación: {e}")
            return {'error': str(e)}
    
    def print_verification_summary(self, verification: Dict):
        """Imprimir resumen de verificación"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 RESUMEN DE VERIFICACIÓN")
        logger.info("=" * 60)
        logger.info(f"🏨 Hoteles verificados: {verification['hotels_verified']}")
        logger.info(f"✅ Verificaciones exitosas: {verification['successful_verifications']}")
        logger.info(f"❌ Verificaciones fallidas: {verification['failed_verifications']}")
        logger.info(f"📅 Fechas esperadas: {verification['total_dates_expected']}")
        logger.info(f"💰 Precios encontrados: {verification['total_prices_found']}")
        logger.info(f"📈 Cobertura general: {verification['overall_coverage']}%")
        
        # Mostrar comparación si está disponible
        if verification.get('comparison'):
            comp = verification['comparison']
            logger.info(f"\n🔄 COMPARACIÓN CON SCRAPING:")
            logger.info(f"   Syncs del scraping: {comp['scraping_syncs']}")
            logger.info(f"   Precios verificados: {comp['verification_prices']}")
            logger.info(f"   Consistencia: {comp['match_percentage']}% - {comp['consistency_check']}")
        
        # Detalles por hotel
        logger.info(f"\n📋 DETALLES POR HOTEL:")
        for result in verification['hotel_results']:
            if result.get('success'):
                logger.info(f"   🏨 {result['hotel_name']}: {result['coverage_percentage']}% ({result['found_prices']}/{result['expected_dates']})")
                if result.get('price_analysis', {}).get('avg_rate'):
                    avg_rate = result['price_analysis']['avg_rate']
                    logger.info(f"      💰 Precio promedio: €{avg_rate}")
            else:
                logger.info(f"   ❌ {result.get('hotel_name', 'Hotel desconocido')}: {result.get('error')}")
    
    def save_verification_results(self, verification: Dict, filename: str = None):
        """Guardar resultados de verificación"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'verification_results_{timestamp}.json'
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(verification, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Verificación guardada en: {filename}")
        except Exception as e:
            logger.error(f"❌ Error guardando verificación: {e}")


def main():
    """Función principal"""
    print("🔍 VERIFICADOR DE SCRAPING MASIVO")
    print("=" * 40)
    
    # Buscar archivos de resultados recientes
    import glob
    result_files = glob.glob('massive_scraping_results_*.json')
    result_files.sort(reverse=True)  # Más reciente primero
    
    selected_file = None
    if result_files:
        print(f"\nArchivos de resultados encontrados:")
        for i, file in enumerate(result_files[:5], 1):
            print(f"{i}. {file}")
        
        try:
            choice = input(f"\nSeleccionar archivo para comparación (1-{min(5, len(result_files))}) o Enter para omitir: ").strip()
            if choice and choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(result_files):
                    selected_file = result_files[idx]
                    print(f"✅ Seleccionado: {selected_file}")
        except:
            pass
    
    # Inicializar verificador
    verifier = MassiveScrapingVerifier()
    
    try:
        # Ejecutar verificación
        verification_results = verifier.verify_massive_scraping(selected_file)
        
        # Mostrar resumen
        verifier.print_verification_summary(verification_results)
        
        # Guardar resultados
        verifier.save_verification_results(verification_results)
        
        print("\n✅ VERIFICACIÓN COMPLETADA")
        
    except Exception as e:
        print(f"\n❌ Error en verificación: {e}")
        logger.error(f"Error crítico: {e}", exc_info=True)


if __name__ == "__main__":
    main()
