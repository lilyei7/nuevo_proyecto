#!/usr/bin/env python3
"""
🔧 CORRECCIÓN DEL SISTEMA DE VERIFICACIÓN MATEMÁTICA
==================================================

Solución para los errores de verificación matemática identificados:
1. Tolerancia para redondeos
2. Verificación en tiempo real
3. Registro detallado de discrepancias
"""

import logging
from price_verification import PriceVerificationEngine, PriceData
from datetime import datetime

class EnhancedPriceVerificationEngine(PriceVerificationEngine):
    """
    🔧 VERIFICADOR MATEMÁTICO MEJORADO CON TOLERANCIA PARA REDONDEOS
    """
    
    def __init__(self, tolerance: float = 2.00):  # Tolerancia de $2 para redondeos
        """
        Args:
            tolerance: Tolerancia para comparaciones (por defecto $2.00)
        """
        super().__init__(tolerance)
        self.verification_log = []
    
    def verify_price_calculation(self, price_data: PriceData) -> dict:
        """
        🔍 VERIFICAR CÁLCULO CON TOLERANCIA MEJORADA Y LOGGING DETALLADO
        """
        result = super().verify_price_calculation(price_data)
        
        # Agregar análisis de discrepancias
        if not result['overall_valid']:
            discrepancy_analysis = self._analyze_discrepancies(price_data)
            result['discrepancy_analysis'] = discrepancy_analysis
            
            # Log detallado para debugging
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'hotel_id': price_data.hotel_id,
                'date': price_data.date,
                'discrepancies': discrepancy_analysis,
                'raw_data': {
                    'base_price': price_data.base_price,
                    'taxes': price_data.taxes,
                    'subtotal': price_data.subtotal,
                    'margin_percent': price_data.margin_percent,
                    'margin_amount': price_data.margin_amount,
                    'final_price': price_data.final_price
                }
            }
            self.verification_log.append(log_entry)
        
        return result
    
    def _analyze_discrepancies(self, price_data: PriceData) -> dict:
        """
        📊 ANALIZAR DISCREPANCIAS EN DETALLE
        """
        analysis = {}
        
        # Calcular valores esperados
        expected_subtotal = price_data.base_price + price_data.taxes
        expected_margin = expected_subtotal * (price_data.margin_percent / 100.0)
        expected_final = expected_subtotal + expected_margin
        
        # Análisis de discrepancias
        subtotal_diff = price_data.subtotal - expected_subtotal
        margin_diff = price_data.margin_amount - expected_margin
        final_diff = price_data.final_price - expected_final
        
        analysis['subtotal_discrepancy'] = {
            'expected': expected_subtotal,
            'actual': price_data.subtotal,
            'difference': subtotal_diff,
            'percentage_error': (abs(subtotal_diff) / expected_subtotal * 100) if expected_subtotal > 0 else 0
        }
        
        analysis['margin_discrepancy'] = {
            'expected': expected_margin,
            'actual': price_data.margin_amount,
            'difference': margin_diff,
            'percentage_error': (abs(margin_diff) / expected_margin * 100) if expected_margin > 0 else 0
        }
        
        analysis['final_price_discrepancy'] = {
            'expected': expected_final,
            'actual': price_data.final_price,
            'difference': final_diff,
            'percentage_error': (abs(final_diff) / expected_final * 100) if expected_final > 0 else 0
        }
        
        # Calcular porcentaje real
        if price_data.subtotal > 0:
            actual_margin_percent = (price_data.margin_amount / price_data.subtotal) * 100
            analysis['actual_margin_percent'] = actual_margin_percent
            analysis['percent_discrepancy'] = actual_margin_percent - price_data.margin_percent
        
        return analysis
    
    def generate_discrepancy_report(self) -> str:
        """
        📋 GENERAR REPORTE DETALLADO DE DISCREPANCIAS
        """
        if not self.verification_log:
            return "📊 No se encontraron discrepancias para reportar."
        
        report = []
        report.append("🔍 REPORTE DETALLADO DE DISCREPANCIAS MATEMÁTICAS")
        report.append("=" * 60)
        
        for entry in self.verification_log:
            report.append(f"\n📅 {entry['date']} - Hotel ID: {entry['hotel_id']}")
            report.append(f"⏰ {entry['timestamp']}")
            
            if 'discrepancy_analysis' in entry:
                analysis = entry['discrepancy_analysis']
                
                if 'subtotal_discrepancy' in analysis:
                    sd = analysis['subtotal_discrepancy']
                    report.append(f"📊 Subtotal: ${sd['actual']:.2f} vs ${sd['expected']:.2f} (diff: ${sd['difference']:.2f})")
                
                if 'margin_discrepancy' in analysis:
                    md = analysis['margin_discrepancy']
                    report.append(f"📈 Margen: ${md['actual']:.2f} vs ${md['expected']:.2f} (diff: ${md['difference']:.2f})")
                
                if 'final_price_discrepancy' in analysis:
                    fd = analysis['final_price_discrepancy']
                    report.append(f"💰 Final: ${fd['actual']:.2f} vs ${fd['expected']:.2f} (diff: ${fd['difference']:.2f})")
                
                if 'actual_margin_percent' in analysis:
                    report.append(f"📊 Porcentaje real: {analysis['actual_margin_percent']:.2f}% vs {entry['raw_data']['margin_percent']}%")
        
        return "\n".join(report)

def test_enhanced_verifier():
    """
    🧪 PROBAR EL VERIFICADOR MEJORADO
    """
    print("🧪 PROBANDO VERIFICADOR MATEMÁTICO MEJORADO")
    print("=" * 50)
    
    # Datos reales del error reportado
    test_cases = [
        {
            'name': 'Caso Real - Error Original',
            'data': {
                'hotel_id': 5,
                'date': '2025-09-29',
                'base_price': 1169.00,
                'taxes': 0.00,
                'subtotal': 1169.00,
                'margin_percent': 62.5,
                'margin_amount': 542.42,  # Valor erróneo reportado
                'final_price': 1898.46,
            }
        },
        {
            'name': 'Caso Real - Datos Corregidos',
            'data': {
                'hotel_id': 5,
                'date': '2025-09-29',
                'base_price': 1169.00,
                'taxes': 0.00,
                'subtotal': 1169.00,
                'margin_percent': 62.5,
                'margin_amount': 730.62,  # Valor matemáticamente correcto
                'final_price': 1899.62,
            }
        },
        {
            'name': 'Caso Real - Porcentaje Corregido',
            'data': {
                'hotel_id': 5,
                'date': '2025-09-29',
                'base_price': 1169.00,
                'taxes': 0.00,
                'subtotal': 1169.00,
                'margin_percent': 62.4,   # Porcentaje que produce 1898.46
                'margin_amount': 729.46,
                'final_price': 1898.46,
            }
        }
    ]
    
    verifier = EnhancedPriceVerificationEngine(tolerance=2.00)
    
    for case in test_cases:
        print(f"\n🔍 {case['name']}:")
        
        price_data = PriceData(
            hotel_id=case['data']['hotel_id'],
            date=case['data']['date'],
            base_price=case['data']['base_price'],
            taxes=case['data']['taxes'],
            subtotal=case['data']['subtotal'],
            margin_percent=case['data']['margin_percent'],
            margin_amount=case['data']['margin_amount'],
            final_price=case['data']['final_price'],
            timestamp=datetime.now().isoformat()
        )
        
        result = verifier.verify_price_calculation(price_data)
        status = "✅ VÁLIDO" if result['overall_valid'] else "❌ INVÁLIDO"
        print(f"  Estado: {status}")
        
        if not result['overall_valid']:
            print("  Errores:")
            for error in result['errors']:
                print(f"    - {error}")
        
        if 'discrepancy_analysis' in result:
            analysis = result['discrepancy_analysis']
            if 'actual_margin_percent' in analysis:
                print(f"  Porcentaje real calculado: {analysis['actual_margin_percent']:.2f}%")
    
    # Mostrar reporte de discrepancias
    print("\n" + verifier.generate_discrepancy_report())

if __name__ == "__main__":
    test_enhanced_verifier()
