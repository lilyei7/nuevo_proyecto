#!/usr/bin/env python3
"""
🧮 VERIFICADOR MATEMÁTICO DE PRECIOS Y PORCENTAJES
==================================================

Verificador que valida que todos los cálculos de precios, impuestos y márgenes
sean matemáticamente correctos después del scraping.

Validaciones:
1. Base + Impuestos = Subtotal
2. Subtotal × (Porcentaje/100) = Margen
3. Subtotal + Margen = Precio Final
4. Porcentaje real vs configurado

Autor: Asistente IA
Fecha: 2025-09-10
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Configurar logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('price_verification')

@dataclass
class PriceData:
    """Estructura de datos para un precio"""
    hotel_id: int
    date: str
    base_price: float
    taxes: float
    subtotal: float
    margin_percent: float
    margin_amount: float
    final_price: float
    timestamp: str

class PriceVerificationEngine:
    """
    🧮 MOTOR DE VERIFICACIÓN MATEMÁTICA DE PRECIOS
    ==============================================
    
    Valida que todos los cálculos sean matemáticamente correctos.
    """
    
    def __init__(self, tolerance: float = 0.01):
        """
        Args:
            tolerance: Tolerancia para comparaciones de punto flotante (centavos)
        """
        self.tolerance = tolerance
        self.verification_results = []
        
    def verify_price_calculation(self, price_data: PriceData) -> Dict:
        """
        🔍 VERIFICAR UN CÁLCULO DE PRECIO INDIVIDUAL
        
        Args:
            price_data: Datos del precio a verificar
            
        Returns:
            Dict con resultado de verificación
        """
        result = {
            'hotel_id': price_data.hotel_id,
            'date': price_data.date,
            'timestamp': price_data.timestamp,
            'validations': {},
            'overall_valid': True,
            'errors': []
        }
        
        # ✅ VALIDACIÓN 1: Base + Impuestos = Subtotal
        expected_subtotal = price_data.base_price + price_data.taxes
        subtotal_valid = abs(price_data.subtotal - expected_subtotal) <= self.tolerance
        
        result['validations']['subtotal'] = {
            'valid': subtotal_valid,
            'expected': expected_subtotal,
            'actual': price_data.subtotal,
            'formula': f"{price_data.base_price:,.2f} + {price_data.taxes:,.2f} = {expected_subtotal:,.2f}",
            'test': f"Subtotal: {price_data.subtotal:,.2f} ≈ {expected_subtotal:,.2f}"
        }
        
        if not subtotal_valid:
            result['overall_valid'] = False
            result['errors'].append(f"Subtotal incorrecto: {price_data.subtotal:,.2f} ≠ {expected_subtotal:,.2f}")
        
        # ✅ VALIDACIÓN 2: Subtotal × (Porcentaje/100) = Margen
        expected_margin = price_data.subtotal * (price_data.margin_percent / 100.0)
        margin_valid = abs(price_data.margin_amount - expected_margin) <= self.tolerance
        
        result['validations']['margin'] = {
            'valid': margin_valid,
            'expected': expected_margin,
            'actual': price_data.margin_amount,
            'formula': f"{price_data.subtotal:,.2f} × ({price_data.margin_percent}% / 100) = {expected_margin:,.2f}",
            'test': f"Margen: {price_data.margin_amount:,.2f} ≈ {expected_margin:,.2f}"
        }
        
        if not margin_valid:
            result['overall_valid'] = False
            result['errors'].append(f"Margen incorrecto: {price_data.margin_amount:,.2f} ≠ {expected_margin:,.2f}")
        
        # ✅ VALIDACIÓN 3: Subtotal + Margen = Precio Final
        expected_final = price_data.subtotal + price_data.margin_amount
        final_valid = abs(price_data.final_price - expected_final) <= self.tolerance
        
        result['validations']['final_price'] = {
            'valid': final_valid,
            'expected': expected_final,
            'actual': price_data.final_price,
            'formula': f"{price_data.subtotal:,.2f} + {price_data.margin_amount:,.2f} = {expected_final:,.2f}",
            'test': f"Final: {price_data.final_price:,.2f} ≈ {expected_final:,.2f}"
        }
        
        if not final_valid:
            result['overall_valid'] = False
            result['errors'].append(f"Precio final incorrecto: {price_data.final_price:,.2f} ≠ {expected_final:,.2f}")
        
        # ✅ VALIDACIÓN 4: Porcentaje real vs configurado
        if price_data.subtotal > 0:
            real_percent = (price_data.margin_amount / price_data.subtotal) * 100
            percent_valid = abs(real_percent - price_data.margin_percent) <= 0.1  # Tolerancia 0.1%
            
            result['validations']['percentage'] = {
                'valid': percent_valid,
                'expected': price_data.margin_percent,
                'actual': real_percent,
                'formula': f"({price_data.margin_amount:,.2f} / {price_data.subtotal:,.2f}) × 100 = {real_percent:.2f}%",
                'test': f"Porcentaje: {real_percent:.2f}% ≈ {price_data.margin_percent:.2f}%"
            }
            
            if not percent_valid:
                result['overall_valid'] = False
                result['errors'].append(f"Porcentaje incorrecto: {real_percent:.2f}% ≠ {price_data.margin_percent:.2f}%")
        
        return result
    
    def verify_scraping_results(self, results: List[Dict]) -> Dict:
        """
        🔍 VERIFICAR MÚLTIPLES RESULTADOS DE SCRAPING
        
        Args:
            results: Lista de resultados de scraping
            
        Returns:
            Dict con resumen de verificación
        """
        log.info("🧮 Iniciando verificación matemática de resultados...")
        
        verification_summary = {
            'total_prices': len(results),
            'valid_prices': 0,
            'invalid_prices': 0,
            'verification_timestamp': datetime.now().isoformat(),
            'detailed_results': [],
            'summary_errors': []
        }
        
        for result_data in results:
            try:
                # Extraer valores base
                base_price = float(result_data.get('base_price', 0))
                taxes = float(result_data.get('taxes', 0))
                subtotal_from_data = float(result_data.get('subtotal', 0))
                
                # Si no hay subtotal, calcularlo
                if subtotal_from_data == 0 and (base_price > 0 or taxes > 0):
                    calculated_subtotal = base_price + taxes
                else:
                    calculated_subtotal = subtotal_from_data
                
                # Convertir a PriceData
                price_data = PriceData(
                    hotel_id=result_data.get('hotel_id', 0),
                    date=result_data.get('checkin', result_data.get('checkin_date', result_data.get('date', 'N/A'))),
                    base_price=base_price,
                    taxes=taxes,
                    subtotal=calculated_subtotal,
                    margin_percent=float(result_data.get('margin_percent', result_data.get('price_percent', 0))),
                    margin_amount=float(result_data.get('margin_amount', 0)),
                    final_price=float(result_data.get('price', result_data.get('final_price', 0))),
                    timestamp=result_data.get('timestamp', result_data.get('scraped_at', datetime.now().isoformat()))
                )
                
                # Verificar este precio
                verification_result = self.verify_price_calculation(price_data)
                verification_summary['detailed_results'].append(verification_result)
                
                if verification_result['overall_valid']:
                    verification_summary['valid_prices'] += 1
                    log.info(f"✅ {price_data.date}: Cálculos correctos - ${price_data.final_price:,.2f}")
                else:
                    verification_summary['invalid_prices'] += 1
                    log.error(f"❌ {price_data.date}: Errores encontrados")
                    for error in verification_result['errors']:
                        log.error(f"   ❌ {error}")
                        verification_summary['summary_errors'].append(f"{price_data.date}: {error}")
                
            except Exception as e:
                verification_summary['invalid_prices'] += 1
                error_msg = f"Error procesando resultado: {e}"
                log.error(f"❌ {error_msg}")
                verification_summary['summary_errors'].append(error_msg)
        
        # 📊 RESUMEN FINAL
        success_rate = (verification_summary['valid_prices'] / verification_summary['total_prices']) * 100 if verification_summary['total_prices'] > 0 else 0
        
        log.info("📊 RESUMEN DE VERIFICACIÓN MATEMÁTICA:")
        log.info(f"   📈 Precios válidos: {verification_summary['valid_prices']}/{verification_summary['total_prices']} ({success_rate:.1f}%)")
        log.info(f"   ❌ Precios con errores: {verification_summary['invalid_prices']}")
        
        if verification_summary['invalid_prices'] == 0:
            log.info("🎉 ¡TODOS LOS CÁLCULOS SON CORRECTOS!")
        else:
            log.warning("⚠️ Se encontraron errores matemáticos en algunos cálculos")
        
        verification_summary['success_rate'] = success_rate
        return verification_summary
    
    def print_detailed_verification(self, verification_result: Dict):
        """
        📋 IMPRIMIR VERIFICACIÓN DETALLADA DE UN PRECIO
        """
        print(f"\n🔍 VERIFICACIÓN DETALLADA - {verification_result['date']}")
        print("="*60)
        
        for validation_name, validation_data in verification_result['validations'].items():
            status = "✅" if validation_data['valid'] else "❌"
            print(f"{status} {validation_name.upper()}: {validation_data['test']}")
            print(f"   Fórmula: {validation_data['formula']}")
            
        if verification_result['errors']:
            print(f"\n❌ ERRORES ENCONTRADOS:")
            for error in verification_result['errors']:
                print(f"   • {error}")
        
        print()

def verify_from_json_file(json_file_path: str, output_file: Optional[str] = None) -> Dict:
    """
    🔍 VERIFICAR RESULTADOS DESDE ARCHIVO JSON
    
    Args:
        json_file_path: Ruta al archivo JSON con resultados
        output_file: Archivo donde guardar el reporte (opcional)
        
    Returns:
        Dict con resumen de verificación
    """
    try:
        log.info(f"📁 Cargando resultados desde: {json_file_path}")
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extraer lista de resultados (puede estar en diferentes formatos)
        if isinstance(data, list):
            results = data
        elif isinstance(data, dict):
            results = data.get('results', data.get('scraping_results', [data]))
        else:
            raise ValueError("Formato de JSON no reconocido")
        
        log.info(f"📊 Encontrados {len(results)} resultados para verificar")
        
        # Crear verificador y ejecutar
        verifier = PriceVerificationEngine()
        verification_summary = verifier.verify_scraping_results(results)
        
        # Guardar reporte si se especifica
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(verification_summary, f, indent=2, ensure_ascii=False)
            log.info(f"💾 Reporte guardado en: {output_file}")
        
        return verification_summary
        
    except Exception as e:
        log.error(f"❌ Error verificando desde JSON: {e}")
        return {}

def verify_single_calculation(base: float, taxes: float, margin_percent: float) -> Dict:
    """
    🧮 VERIFICAR UN CÁLCULO INDIVIDUAL (función de utilidad)
    
    Args:
        base: Precio base
        taxes: Impuestos  
        margin_percent: Porcentaje de margen
        
    Returns:
        Dict con resultado de verificación
    """
    subtotal = base + taxes
    margin_amount = subtotal * (margin_percent / 100)
    final_price = subtotal + margin_amount
    
    price_data = PriceData(
        hotel_id=999,
        date="test",
        base_price=base,
        taxes=taxes,
        subtotal=subtotal,
        margin_percent=margin_percent,
        margin_amount=margin_amount,
        final_price=final_price,
        timestamp=datetime.now().isoformat()
    )
    
    verifier = PriceVerificationEngine()
    return verifier.verify_price_calculation(price_data)

if __name__ == "__main__":
    # 🧪 TEST DE EJEMPLO
    log.info("🧪 Ejecutando test de verificación matemática...")
    
    # Ejemplo: Base $1000, Impuestos $160, Margen 20%
    test_result = verify_single_calculation(base=1000.00, taxes=160.00, margin_percent=20.0)
    
    verifier = PriceVerificationEngine()
    verifier.print_detailed_verification(test_result)
    
    if test_result['overall_valid']:
        log.info("🎉 Test de verificación exitoso!")
    else:
        log.error("❌ Test de verificación falló!")
