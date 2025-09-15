#!/usr/bin/env python3
"""
🤖 SCRAPER INTELIGENTE CON DETECCIÓN DE DISPONIBILIDAD - INTEGRADO CON OTASYNC
============================================================================

Este módulo implementa un scraper inteligente que:

CARACTERÍSTICAS PRINCIPALES:
- 🎯 Detección automática de disponibilidad de hoteles
- 🔄 Búsqueda de fechas alternativas cuando no hay disponibilidad
- 📊 Scraping de 20 fechas automáticamente por hotel
- 🔗 Integración completa con OTASync API
- 📡 Logging en tiempo real vía WebSocket
- 🛡️ Sistema anti-detección avanzado
- ⚡ Configuración optimizada para headless mode

FLUJO DE TRABAJO:
1. 🏨 Recibe URL de Booking.com del hotel
2. 🎯 Intenta scraping para fechas específicas  
3. 🔍 Detecta si el hotel no está disponible
4. 📅 Si no disponible, busca fechas alternativas
5. 💰 Extrae precios y aplica márgenes configurados
6. 🔄 Sincroniza con OTASync API en tiempo real
7. 📊 Emite logs detallados vía WebSocket

INTEGRACIÓN OTASYNC:
- Aplicación automática de márgenes de precio
- Sincronización inmediata con API de OTASync
- Logging detallado de cada paso del proceso
- Manejo de errores robusto

ANTI-DETECCIÓN:
- User agents rotativos
- Headers personalizados
- Delays aleatorios entre requests
- Desactivación de imágenes y plugins
- Configuración optimizada de Chrome

Autor: Sistema de Scraping Hotelero
Última actualización: 27 de agosto de 2025
"""

# ===== IMPORTACIONES ESENCIALES =====
import time
import random
import logging
import re
import os
import sys
import importlib.util
import argparse
import json
from datetime import date, timedelta, datetime
from typing import Dict, List, Optional, Tuple

# Importar verificador de precios
try:
    from price_verification import PriceVerificationEngine, PriceData
    HAVE_PRICE_VERIFIER = True
except ImportError:
    HAVE_PRICE_VERIFIER = False

# Asegurar path para imports locales
_HERE = os.path.abspath(os.path.dirname(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Default number of scraping days (configurable via env SCRAPING_DAYS)
DEFAULT_SCRAPING_DAYS = int(os.environ.get('SCRAPING_DAYS', '20'))

# ===== INTEGRACIÓN WEBSOCKET Y EVENTOS SSE (OPCIONAL) =====
try:
    from socket_manager import emit_log_message as emit_scraper_log
    HAVE_SOCKETIO = True
    HAVE_SSE = True  # Para compatibilidad con código existente
    print("✅ DEBUG: socket_manager import successful")
except ImportError as e:
    HAVE_SOCKETIO = False
    HAVE_SSE = False  # Para compatibilidad con código existente
    print(f"❌ DEBUG: socket_manager import failed: {e}")
    def emit_scraper_log(*args, **kwargs):
        """Función dummy si SocketIO no está disponible"""
        print(f"🔇 SOCKETIO: {args[0] if args else 'no message'}")
        pass

# Función dummy para broadcast_scraping_event si no está disponible
def broadcast_scraping_event(event_type, data):
    """Función dummy para eventos de scraping"""
    print(f"📡 SSE: {event_type} - {data}")
    pass

# ===== INTEGRACIÓN SELENIUM (REQUERIDA) =====
HAVE_SELENIUM = True
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    print("✅ DEBUG: Selenium importado correctamente")
except Exception as e:
    HAVE_SELENIUM = False
    print(f"❌ DEBUG: Selenium no disponible: {e}")

# ===== MÓDULOS INTERNOS DEL SISTEMA =====
try:
    from scraper.utils import parse_booking_url, build_url_from_template
    from scraper.db import DatabaseManager
    print("✅ DEBUG: Módulos internos importados correctamente")
except Exception as e:
    print(f"❌ DEBUG: Error importando módulos internos: {e}")
    # Crear fallbacks básicos
    def parse_booking_url(url):
        return {"base_url": url}
    def build_url_from_template(url, checkin, checkout):
        return f"{url}&checkin={checkin}&checkout={checkout}"
    class DatabaseManager:
        def __init__(self, db_path=None):
            pass
        def get_all_hotels(self):
            return []
        def get_hotel_by_id(self, hotel_id):
            return None
        def get_hotel_otasync_info(self, hotel_id):
            return None

# ===== INTEGRACIÓN OTASYNC (FUNCIONAL) =====
try:
    from otasync_api_client_official import OTASyncAPIClient
    print("✅ DEBUG: OTASync API Client importado correctamente")
    HAVE_OTASYNC = True
except ImportError as e:
    print(f"❌ DEBUG: OTASync API Client no disponible: {e}")
    HAVE_OTASYNC = False

# Configuración de logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class IntelligentScraper:
    """
    🤖 SCRAPER INTELIGENTE CON DETECCIÓN DE DISPONIBILIDAD
    =====================================================
    
    Scraper avanzado que detecta automáticamente disponibilidad y busca alternativas.
    
    Características:
    - Detección inteligente de no disponibilidad
    - Búsqueda automática de fechas alternativas  
    - Sistema anti-detección robusto
    - Integración con WebSocket para logs en tiempo real
    - Configuración optimizada para headless mode
    
    Args:
        headless (bool): Si usar modo headless (True para producción)
        
    Attributes:
        driver: Instancia de WebDriver de Chrome
        emit_progress: Callback para emitir progreso via WebSocket
    """
    
    def __init__(self, headless: bool = True):
        if not HAVE_SELENIUM:
            raise RuntimeError("Selenium no está disponible en este entorno")
        self.headless = headless
        self.driver = None
        self.emit_progress = None  # Para conectar con WebSocket
        
    def setup_driver(self):
        """
        🔧 CONFIGURACIÓN DE CHROME DRIVER OPTIMIZADO
        ============================================
        
        Configura Chrome WebDriver con opciones anti-detección y optimización.
        
        Características de la configuración:
        - Modo headless optimizado para servidores
        - Headers y user agents realistas
        - Desactivación de recursos innecesarios (imágenes, plugins)
        - Configuraciones anti-detección
        - Optimización de memoria y rendimiento
        
        Returns:
            webdriver.Chrome: Driver configurado y listo para usar
            
        Raises:
            Exception: Si no se puede inicializar el driver
        """
        # Asegurar que tenemos acceso a os
        import os
        from pathlib import Path
        
        # Cargar variables de entorno desde .env si existe
        try:
            env_path = Path(__file__).resolve().parent / '.env'
            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ.setdefault(key, value)
        except Exception as e:
            log.debug(f"No se pudo cargar .env: {e}")
        
        options = Options()
        
        # ===== CONFIGURACIÓN HEADLESS =====
        if self.headless:
            options.add_argument("--headless=new")           # Nuevo modo headless más estable
            options.add_argument("--window-size=1920,1080")  # Resolución estándar
            options.add_argument("--start-maximized")        # Ventana maximizada
        
        # ===== CONFIGURACIÓN ANTI-DETECCIÓN =====
        options.add_argument("--no-sandbox")                                    # Desactivar sandbox
        options.add_argument("--disable-dev-shm-usage")                        # Optimización memoria
        options.add_argument("--disable-blink-features=AutomationControlled")  # Anti-detección
        options.add_argument("--disable-extensions")                           # Sin extensiones
        options.add_argument("--disable-plugins")                              # Sin plugins
        options.add_argument("--disable-images")                               # Sin imágenes
        options.add_argument("--disable-gpu")                                  # Sin GPU
        options.add_argument("--disable-web-security")                         # Desactivar seguridad web
        options.add_argument("--disable-features=VizDisplayCompositor")        # Optimización
        
        # ===== OPTIMIZACIÓN DE RENDIMIENTO MEJORADA =====
        options.add_argument("--disable-background-timer-throttling")          # Sin throttling
        options.add_argument("--disable-backgrounding-occluded-windows")       # Sin backgrounding
        options.add_argument("--disable-renderer-backgrounding")               # Sin renderer bg
        options.add_argument("--memory-pressure-off")                          # Sin presión memoria
        
        # ===== OPTIMIZACIONES ADICIONALES DE VELOCIDAD =====
        options.add_argument("--disable-background-networking")                # Sin networking bg
        options.add_argument("--disable-sync")                                 # Sin sincronización
        options.add_argument("--disable-translate")                            # Sin traductor
        options.add_argument("--disable-ipc-flooding-protection")              # Sin protección IPC
        options.add_argument("--disable-hang-monitor")                         # Sin monitor colgado
        options.add_argument("--disable-prompt-on-repost")                     # Sin prompts repost
        options.add_argument("--disable-client-side-phishing-detection")       # Sin detección phishing
        options.add_argument("--disable-component-update")                     # Sin updates componentes
        options.add_argument("--disable-default-apps")                         # Sin apps por defecto
        options.add_argument("--aggressive-cache-discard")                     # Cache agresivo
        options.add_argument("--disable-features=TranslateUI")                 # Sin UI traducción
        options.add_argument("--disable-features=MediaRouter")                 # Sin media router
        
        # ===== CONFIGURACIÓN DE RED OPTIMIZADA =====
        options.add_argument("--aggressive")                                   # Modo agresivo
        options.add_argument("--disable-logging")                              # Sin logging interno
        
        # ===== USER AGENT REALISTA =====
        options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")
        
        # ===== DESACTIVAR FLAGS DE AUTOMATIZACIÓN =====
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # ===== CONFIGURACIONES DE CONTENIDO =====
        # Desactivar imágenes, plugins, popups, etc. para optimización
        prefs = {
            "profile.default_content_setting_values": {
                "images": 2,          # Bloquear imágenes
                "plugins": 2,         # Bloquear plugins  
                "popups": 2,          # Bloquear popups
                "geolocation": 2,     # Bloquear geolocalización
                "notifications": 2,   # Bloquear notificaciones
                "media_stream": 2,    # Bloquear media stream
            },
            "profile.managed_default_content_settings": {
                "images": 2           # Bloquear imágenes a nivel managed
            }
        }
        options.add_experimental_option("prefs", prefs)
        
        # ===== CREAR DRIVER CON CONFIGURACIÓN OPTIMIZADA =====
        try:
            from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
            caps = DesiredCapabilities.CHROME.copy()
            caps['pageLoadStrategy'] = 'eager'

            # Prefer using webdriver-manager to install a compatible chromedriver
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options, desired_capabilities=caps)
            except Exception:
                # Fallback to default constructor which uses PATH
                driver = webdriver.Chrome(options=options, desired_capabilities=caps)
        except Exception:
            # Final fallback without desired_capabilities (older selenium)
            try:
                driver = webdriver.Chrome(options=options)
            except Exception as e:
                log.error(f"No se pudo inicializar Chrome WebDriver: {e}")
                raise
        
        # Scripts anti-detección
        try:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es']})")
            driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        except Exception:
            pass

        # Timeouts optimizados para velocidad (configurables via env)
        self.page_load_timeout = int(os.environ.get('PAGE_LOAD_TIMEOUT', '20'))  # Reducido de 60 a 20
        self.implicit_wait = int(os.environ.get('IMPLICIT_WAIT', '3'))  # Reducido de 5 a 3  
        self.explicit_wait = int(os.environ.get('EXPLICIT_WAIT', '15'))  # Reducido de 30 a 15
        
        # Configuración de velocidad adicional
        self.fast_mode = os.environ.get('FAST_SCRAPING_MODE', 'true').lower() == 'true'
        self.min_delay = float(os.environ.get('MIN_REQUEST_DELAY', '1.0'))  # Mínimo delay
        self.max_delay = float(os.environ.get('MAX_REQUEST_DELAY', '2.5'))  # Máximo delay
        
        if self.fast_mode:
            log.info("🚀 MODO RÁPIDO ACTIVADO: Timeouts reducidos y delays optimizados")

        driver.set_page_load_timeout(self.page_load_timeout)
        driver.implicitly_wait(self.implicit_wait)

        return driver
    
    def detect_availability_status(self, html_content: str) -> Dict:
        """Detectar el estado de disponibilidad desde el HTML"""
        
        # Patrones de no disponibilidad en español y inglés
        no_availability_patterns = [
            r"No tenemos disponibilidad",
            r"No hay disponibilidad",
            r"Sin disponibilidad",
            r"Agotado",
            r"No disponible",
            r"no está disponible",
            r"fecha no disponible",
            r"No availability",
            r"Sold out",
            r"Not available",
            r"No rooms available"
        ]
        
        # Patrones de disponibilidad limitada
        limited_patterns = [
            r"Solo quedan? \d+",
            r"Últimas? \d+ habitaciones?",
            r"¡Solo \d+",
            r"Disponibilidad limitada",
            r"Only \d+ left",
            r"Last \d+ rooms?"
        ]
        
        # Patrones de precios con impuestos incluidos (mejorados)
        price_patterns = [
            r"MXN\s*\$?\s*([0-9,]+(?:\.\d{2})?)",              # MXN $1,234.56
            r"\$\s*([0-9,]+(?:\.\d{2})?)\s*MXN",              # $1,234.56 MXN
            r"([0-9,]+(?:\.\d{2})?)\s*pesos",                  # 1,234 pesos
            r"\$([0-9,]+(?:\.\d{2})?)",                        # $1,234.56
            r"([0-9,]+(?:\.\d{2})?)\s*MXN",                    # 1,234.56 MXN
            r"Total[:\s]*\$?([0-9,]+(?:\.\d{2})?)",            # Total: $1,234.56
            r"impuestos\s+incluidos[:\s]*\$?([0-9,]+(?:\.\d{2})?)", # impuestos incluidos: $1,234
            r"precio\s+final[:\s]*\$?([0-9,]+(?:\.\d{2})?)",   # precio final: $1,234
            r"todo\s+incluido[:\s]*\$?([0-9,]+(?:\.\d{2})?)"   # todo incluido: $1,234
        ]
        
        result = {
            "available": True,
            "message": "",
            "prices_found": [],
            "alternative_dates": False,
            "limited_availability": False
        }
        
        # Primero buscar disponibilidad limitada (tiene prioridad)
        limited_found = False
        for pattern in limited_patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                result["limited_availability"] = True
                result["available"] = True  # Sigue siendo disponible
                result["message"] = f"Disponibilidad limitada: {match.group()}"
                log.info(f"⚠️ Detectado: {match.group()}")
                limited_found = True
                break
        
        # Solo verificar no disponibilidad si no hay disponibilidad limitada
        if not limited_found:
            for pattern in no_availability_patterns:
                if re.search(pattern, html_content, re.IGNORECASE):
                    result["available"] = False
                    result["message"] = f"No disponible: {pattern}"
                    log.warning(f"🚫 Detectado: {pattern}")
                    break
        
        # Buscar precios
        for pattern in price_patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                try:
                    # Limpiar y convertir precio
                    price_str = match.replace(",", "")
                    price = float(price_str)
                    if 1000 <= price <= 50000:  # Rango realista para hoteles en México
                        result["prices_found"].append(price)
                except:
                    pass
        
        # Detectar fechas alternativas sugeridas
        if "Alojamientos similares" in html_content or "fechas alternativas" in html_content or "alternative dates" in html_content:
            result["alternative_dates"] = True
            
        return result
    
    def generate_alternative_dates(self, original_checkin: date, days_ahead: int = 14) -> List[Tuple[date, date]]:
        """Generar fechas alternativas inteligentemente"""
        alternatives = []
        today = date.today()
        
        # Fechas hacia adelante (próximos 14 días)
        for i in range(1, days_ahead + 1):
            new_checkin = original_checkin + timedelta(days=i)
            new_checkout = new_checkin + timedelta(days=1)
            alternatives.append((new_checkin, new_checkout))
        
        # Fechas hacia atrás (solo si es mayor a hoy)
        for i in range(1, 7):
            new_checkin = original_checkin - timedelta(days=i)
            if new_checkin >= today:
                new_checkout = new_checkin + timedelta(days=1)
                alternatives.append((new_checkin, new_checkout))
        
        return alternatives
    
    def extract_prices_and_taxes_from_page(self) -> Dict:
        """
        Extraer precios BASE y los IMPUESTOS POR SEPARADO de Booking.com
        Retorna: {'base_price': float, 'taxes': float, 'total_price': float}
        """
        result = {
            'base_price': 0.0,
            'taxes': 0.0,
            'total_price': 0.0,
            'all_prices_found': []
        }
        
        try:
            log.debug("💰 Buscando precio base + impuestos por separado...")
            
            # 🏷️ SELECTORES PARA PRECIO BASE (sin impuestos)
            base_price_selectors = [
                '.bui-price-display__value',
                '.prco-valign-middle-helper', 
                '[data-testid="price-and-discounted-price"] .bui-price-display__value',
                '.sr-hotel__price-option .bui-price-display__value',
                '.hprt-price-price'
            ]
            
            # 🧾 SELECTORES PARA IMPUESTOS
            tax_selectors = [
                '*[class*="tax"]',
                '*[class*="fee"]',
                '*[class*="charge"]',
                '[data-testid*="tax"]',
                '.bui-price-display__tax',
                '.sr-hotel__price-tax'
            ]
            
            # 💰 PATRONES PARA EXTRAER PRECIOS
            price_patterns = [
                r'MXN\s*\$?\s*([0-9,]+(?:\.\d{2})?)',
                r'\$\s*([0-9,]+(?:\.\d{2})?)\s*MXN',
                r'([0-9,]+(?:\.\d{2})?)\s*pesos',
                r'\$([0-9,]+(?:\.\d{2})?)'
            ]
            
            # 🧾 PATRONES ESPECÍFICOS PARA IMPUESTOS
            tax_patterns = [
                r'impuestos?\s*[:\-]?\s*\$?([0-9,]+(?:\.\d{2})?)',
                r'tax(?:es)?\s*[:\-]?\s*\$?([0-9,]+(?:\.\d{2})?)', 
                r'tasas?\s*[:\-]?\s*\$?([0-9,]+(?:\.\d{2})?)',
                r'cargos?\s*[:\-]?\s*\$?([0-9,]+(?:\.\d{2})?)',
                r'fees?\s*[:\-]?\s*\$?([0-9,]+(?:\.\d{2})?)',
                r'incluye.*impuestos?\s*\$?([0-9,]+(?:\.\d{2})?)',
                r'\+\s*\$?([0-9,]+(?:\.\d{2})?)\s*(?:impuestos?|tax|tasas?)'
            ]
            
            base_prices = []
            taxes = []
            
            # 🎯 PASO 1: Buscar precios base
            for selector in base_price_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            price_text = element.text.strip()
                            
                            # Solo considerar si no dice "impuestos incluidos"
                            text_lower = price_text.lower()
                            if 'impuestos incluidos' not in text_lower and 'taxes included' not in text_lower:
                                for pattern in price_patterns:
                                    matches = re.findall(pattern, price_text, re.IGNORECASE)
                                    for match in matches:
                                        try:
                                            price_val = float(match.replace(',', ''))
                                            if 1000 <= price_val <= 50000:
                                                base_prices.append(price_val)
                                                log.debug(f"💰 Precio base: ${price_val:,.2f}")
                                        except ValueError:
                                            continue
                            
                except Exception as e:
                    log.debug(f"Error con selector base {selector}: {e}")
            
            # 🎯 PASO 2: Buscar impuestos específicamente
            for selector in tax_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            tax_text = element.text.strip()
                            
                            for pattern in tax_patterns:
                                matches = re.findall(pattern, tax_text, re.IGNORECASE)
                                for match in matches:
                                    try:
                                        tax_val = float(match.replace(',', ''))
                                        if 10 <= tax_val <= 5000:  # Rango realista para impuestos
                                            taxes.append(tax_val)
                                            log.debug(f"🧾 Impuesto: ${tax_val:,.2f}")
                                    except ValueError:
                                        continue
                        
                except Exception as e:
                    log.debug(f"Error con selector impuestos {selector}: {e}")
            
            # 🎯 PASO 3: Buscar en HTML general
            html = self.driver.page_source
            
            # Buscar patrones de impuestos en todo el HTML
            for pattern in tax_patterns:
                matches = re.finditer(pattern, html, re.IGNORECASE)
                for match in matches:
                    try:
                        tax_val = float(match.group(1).replace(',', ''))
                        if 10 <= tax_val <= 5000:
                            taxes.append(tax_val)
                            log.debug(f"🧾 Impuesto en HTML: ${tax_val:,.2f}")
                    except ValueError:
                        continue
            
            # Si no encontramos impuestos separados, buscar frases como "impuestos incluidos: X"
            if not taxes:
                included_tax_patterns = [
                    r'impuestos?\s+incluidos?\s*[:\-]?\s*\$?([0-9,]+(?:\.\d{2})?)',
                    r'incluye\s+\$?([0-9,]+(?:\.\d{2})?)\s*(?:de\s+)?impuestos?',
                    r'taxes?\s+included?\s*[:\-]?\s*\$?([0-9,]+(?:\.\d{2})?)'
                ]
                
                for pattern in included_tax_patterns:
                    matches = re.finditer(pattern, html, re.IGNORECASE)
                    for match in matches:
                        try:
                            tax_val = float(match.group(1).replace(',', ''))
                            if 10 <= tax_val <= 5000:
                                taxes.append(tax_val)
                                log.debug(f"🧾 Impuesto incluido: ${tax_val:,.2f}")
                        except ValueError:
                            continue
            
            # 📊 CALCULAR RESULTADO FINAL
            if base_prices:
                result['base_price'] = min(base_prices)  # Precio más bajo
                result['all_prices_found'] = list(set(base_prices))
            
            if taxes:
                result['taxes'] = max(taxes)  # Impuesto más alto (más completo)
            
            # Si no encontramos impuestos separados, estimar 16% (IVA México)
            if result['base_price'] > 0 and result['taxes'] == 0:
                estimated_tax = result['base_price'] * 0.16  # IVA 16%
                result['taxes'] = estimated_tax
                log.info(f"🧾 Impuesto estimado (16% IVA): ${estimated_tax:,.2f}")
            
            result['total_price'] = result['base_price'] + result['taxes']
            
            # 📊 LOGGING DETALLADO
            if result['base_price'] > 0:
                log.info(f"💰 Precio base encontrado: ${result['base_price']:,.2f}")
                log.info(f"🧾 Impuestos encontrados: ${result['taxes']:,.2f}")
                log.info(f"💵 Precio total (base + impuestos): ${result['total_price']:,.2f}")
            else:
                log.warning("⚠️ No se encontraron precios base válidos")
                
        except Exception as e:
            log.error(f"❌ Error extrayendo precios y impuestos: {e}")
        
        return result

    def extract_prices_from_page(self) -> List[float]:
        """Método legacy - ahora usa la nueva función de precios + impuestos"""
        price_data = self.extract_prices_and_taxes_from_page()
        if price_data['total_price'] > 0:
            return [price_data['total_price']]  # Devuelve precio total (base + impuestos)
        return price_data['all_prices_found']
    
    def scrape_hotel_intelligent(self, hotel_url: str, hotel_id: int, max_attempts: int = 20) -> List[Dict]:
        """
        🏨 SCRAPER INTELIGENTE CON FLUJO COMPLETO:
        ========================================
        1. Scraping de exactamente 20 fechas consecutivas
        2. Aplicación de porcentaje de margen configurado
        3. Guardado en base de datos con timestamp
        4. Sincronización automática con OTASync
        5. Logging detallado de todo el proceso
        """
        log.info(f"🤖 Iniciando scraping inteligente para hotel ID: {hotel_id}")
        log.info(f"🎯 META: Obtener {max_attempts} fechas con precios válidos")
        
        # Emitir progreso inicial
        if self.emit_progress:
            self.emit_progress({
                'status': 'intelligent_start',
                'hotel_id': hotel_id,
                'max_attempts': max_attempts,
                'message': f'🎯 META: {max_attempts} fechas → Aplicar margen → Guardar BD → Sincronizar OTASync'
            })
        
        # Parsear URL base
        template = parse_booking_url(hotel_url)
        if not template:
            log.error("❌ No se pudo parsear la URL")
            return []

        # 🏨 OBTENER CONFIGURACIÓN DEL HOTEL
        try:
            import os  # Importar os para acceso a variables de entorno
            from scraper.db import DatabaseManager
            db_path = os.environ.get('DB_PATH')
            if db_path:
                db = DatabaseManager(db_path=db_path)
            else:
                db = DatabaseManager()
            
            # Obtener información del hotel Y su configuración de margen
            hotel_info = db.get_hotel_otasync_info(hotel_id)
            hotel_basic = db.get_hotel_by_id(hotel_id)
            
            # Obtener nombre del hotel
            hotel_name = "Hotel desconocido"
            if hotel_basic and hotel_basic.get('name'):
                hotel_name = hotel_basic.get('name')
            elif hotel_info and hotel_info.get('name'):
                hotel_name = hotel_info.get('name')
            
            # Configuración de margen
            price_percent = 0.0
            if hotel_info and hotel_info.get('price_percent'):
                price_percent = float(hotel_info.get('price_percent', 0))
            elif hotel_basic and hotel_basic.get('price_percent'):
                price_percent = float(hotel_basic.get('price_percent', 0))
            
            log.info(f"🏨 Hotel: {hotel_name} - Margen configurado: {price_percent}%")
            if self.emit_progress:
                self.emit_progress({
                    'status': 'hotel_config_loaded',
                    'hotel_id': hotel_id,
                    'price_percent': price_percent,
                    'message': f'📊 Margen configurado: {price_percent}%'
                })
                
        except Exception as e:
            log.error(f"❌ Error cargando configuración del hotel: {e}")
            price_percent = 0.0
            db = None

        self.driver = self.setup_driver()
        
        # Importaciones necesarias para el bucle
        from datetime import date, timedelta
        
        results = []
        today = date.today()
        successful_dates = 0
        failed_attempts = 0
        max_failed_attempts = 10  # Máximo de intentos fallidos antes de continuar
        
        try:
            # 🎯 OBJETIVO: Obtener exactamente max_attempts fechas con precios
            days_checked = 0
            max_days_to_check = max_attempts * 3  # Buscar hasta 3x más días si es necesario
            
            log.info(f"🎯 INICIANDO BÚSQUEDA: {max_attempts} fechas objetivo")
            log.info(f"📅 Buscando desde: {today} (máximo {max_days_to_check} días hacia adelante)")
            
            while successful_dates < max_attempts and days_checked < max_days_to_check:
                checkin = today + timedelta(days=days_checked)
                checkout = checkin + timedelta(days=1)
                days_checked += 1
                
                log.info(f"📅 [{successful_dates+1}/{max_attempts}] Probando: {checkin} → {checkout}")
                
                # Emitir progreso por fecha
                if self.emit_progress:
                    self.emit_progress({
                        'status': 'intelligent_date',
                        'hotel_id': hotel_id,
                        'current_date': checkin.isoformat(),
                        'attempt': days_checked,
                        'successful_so_far': successful_dates,
                        'target_dates': max_attempts,
                        'progress_percent': round((successful_dates / max_attempts) * 100, 1)
                    })
                
                try:
                    # Construir URL con fechas específicas
                    url_with_dates = build_url_from_template(hotel_url, checkin, checkout)
                    
                    log.info(f"🌐 Navegando a: {url_with_dates[:100]}...")
                    html_content = None
                    try:
                        self.driver.get(url_with_dates)
                    except Exception as e:
                        log.warning(f"⚠️ Timeout cargando página: {e}")
                        try:
                            html_content = self.driver.execute_script('return document.documentElement.outerHTML')
                        except Exception as e2:
                            log.error(f"❌ Error capturando HTML: {e2}")
                            failed_attempts += 1
                            if failed_attempts >= max_failed_attempts:
                                log.warning(f"⚠️ Muchos errores ({failed_attempts}), continuando...")
                                break
                            continue

                    # Espera optimizada para elementos (más rápida)
                    if not html_content:
                        try:
                            # Espera más corta y específica
                            WebDriverWait(self.driver, 8).until(  # Reducido de explicit_wait a 8 segundos
                                lambda d: d.find_element(By.TAG_NAME, 'body') is not None
                            )
                        except Exception:
                            log.debug("Espera rápida falló, usando contenido actual")
                        title = ''
                        try:
                            title = self.driver.title
                        except Exception:
                            title = ''
                        log.info(f"📄 Página cargada: {title[:60]}...")
                        html_content = self.driver.page_source
                    
                    # Analizar disponibilidad
                    availability = self.detect_availability_status(html_content)
                    
                    if availability["available"]:
                        log.info(f"✅ Hotel disponible para {checkin}")
                        
                        # 💰 Extraer precio base + impuestos por separado
                        price_data = self.extract_prices_and_taxes_from_page()
                        
                        if price_data['base_price'] > 0:
                            base_price = price_data['base_price']
                            taxes = price_data['taxes']
                            subtotal = base_price + taxes  # PRECIO BASE + IMPUESTOS
                            
                            log.info(f"� Precio base: MXN {base_price:,.2f}")
                            log.info(f"🧾 Impuestos: MXN {taxes:,.2f}")
                            log.info(f"💵 Subtotal (base + impuestos): MXN {subtotal:,.2f}")
                            
                            # 📊 APLICAR MARGEN SOBRE EL SUBTOTAL (base + impuestos)
                            margin_amount = subtotal * (price_percent / 100.0)
                            final_price = subtotal + margin_amount
                            
                            log.info(f"📊 Aplicando margen {price_percent}% sobre subtotal: +MXN {margin_amount:,.2f}")
                            log.info(f"💵 PRECIO FINAL: MXN {final_price:,.2f}")
                            
                            emit_scraper_log(f"💰 {checkin}: Base ${base_price:,.2f} + Impuestos ${taxes:,.2f} + {price_percent}% = ${final_price:,.2f}", 'success', 'scraping')
                            
                            # 📡 ENVIAR EVENTO SSE AL MONITOR EN TIEMPO REAL
                            if HAVE_SSE:
                                broadcast_scraping_event('scraping_result', {
                                    'success': True,
                                    'hotel': hotel_name,
                                    'hotel_id': hotel_id,
                                    'price': final_price,
                                    'base_price': base_price,
                                    'taxes': taxes,
                                    'subtotal': subtotal,
                                    'margin_percent': price_percent,
                                    'margin_amount': margin_amount,
                                    'checkin': checkin,
                                    'timestamp': datetime.now().isoformat()
                                })
                            
                            # 💾 GUARDAR EN BASE DE DATOS CON TIMESTAMP
                            scraped_at = datetime.now()
                            if db:
                                try:
                                    db.insert_scrape(
                                        hotel_id_fk=hotel_id,
                                        checkin=checkin.isoformat(),
                                        checkout=checkout.isoformat(),
                                        price_amount=final_price,
                                        price_currency='MXN',
                                        availability='available',
                                        source_url=url_with_dates,
                                        scraped_at=scraped_at.isoformat(),
                                        base_price=base_price,
                                        margin_percent=price_percent,
                                        margin_amount=margin_amount
                                    )
                                    log.info(f"💾 ✅ Guardado en BD: {checkin} - MXN {final_price:,.2f}")
                                    emit_scraper_log(f"💾 Guardado en BD: {checkin}", 'success', 'database')
                                except Exception as save_error:
                                    log.error(f"❌ Error guardando en BD: {save_error}")
                                    emit_scraper_log(f"❌ Error BD: {str(save_error)}", 'error', 'database')
                            
                            # Crear resultado completo (sincronización OTASync se hará en lote al final)
                            result = {
                                'hotel_id': hotel_id,
                                'checkin_date': checkin.isoformat(),
                                'checkout_date': checkout.isoformat(),
                                'checkin': checkin.isoformat(),  # Para verificador
                                'date': checkin.isoformat(),     # Para verificador alternativo
                                'base_price': base_price,
                                'taxes': taxes,                  # Para verificador
                                'subtotal': subtotal,           # Para verificador
                                'price_percent': price_percent,
                                'margin_percent': price_percent, # Para verificador
                                'margin_amount': margin_amount,
                                'final_price': final_price,
                                'price': final_price,           # Para verificador alternativo
                                'price_currency': 'MXN',
                                'availability': 'available',
                                'method': 'intelligent_scraper',
                                'scraped_at': scraped_at.isoformat(),
                                'timestamp': scraped_at.isoformat(), # Para verificador
                                'source_url': url_with_dates,
                                'otasync_synced': False,  # Se sincronizará en lote al final
                                'all_prices_found': price_data.get('all_prices_found', [])
                            }
                            
                            results.append(result)
                            successful_dates += 1
                            
                            # Progreso detallado (formato solicitado)
                            date_range = f"{checkin.strftime('%d')}-{checkout.strftime('%d')}"
                            if self.emit_progress:
                                progress_message = f"📅 {date_range} ✅ MXN {base_price:,.0f} + {price_percent}% = MXN {final_price:,.0f} 💾✅"
                                
                                self.emit_progress({
                                    'status': 'intelligent_price_found',
                                    'hotel_id': hotel_id,
                                    'checkin_date': checkin.isoformat(),
                                    'base_price': base_price,
                                    'price_percent': price_percent,
                                    'final_price': final_price,
                                    'successful_count': successful_dates,
                                    'target_count': max_attempts,
                                    'progress_percent': round((successful_dates / max_attempts) * 100, 1),
                                    'message': progress_message,
                                    'otasync_synced': False  # Se sincronizará en lote al final
                                })
                                
                                # 📡 ENVIAR EVENTO DE PROGRESO A SSE
                                if HAVE_SSE:
                                    broadcast_scraping_event('progress', {
                                        'current': successful_dates,
                                        'total': max_attempts,
                                        'success': successful_dates,
                                        'errors': days_checked - successful_dates,
                                        'hotel_id': hotel_id,
                                        'hotel_name': hotel_name
                                    })
                            
                            # ¿Alcanzamos el objetivo?
                            if successful_dates >= max_attempts:
                                log.info(f"🎯 ✅ OBJETIVO ALCANZADO: {successful_dates}/{max_attempts} fechas obtenidas")
                                emit_scraper_log(f"🎯 ✅ OBJETIVO ALCANZADO: {successful_dates} fechas", 'success', 'scraping')
                                break
                        else:
                            log.warning(f"⚠️ Hotel disponible pero no se encontró precio base para {checkin}")
                    else:
                        log.warning(f"🚫 {availability['message']} para {checkin}")
                    
                    # Pausa optimizada entre requests usando configuración de velocidad
                    if self.fast_mode:
                        delay = random.uniform(self.min_delay, self.max_delay)  # Modo rápido
                    else:
                        delay = random.uniform(2.0, 4.0) + (days_checked * 0.05)  # Modo conservador
                    log.info(f"⏳ Esperando {delay:.1f}s...")
                    time.sleep(delay)
                    
                except Exception as e:
                    log.error(f"❌ Error scrapeando {checkin}: {e}")
                    failed_attempts += 1
                    if failed_attempts >= max_failed_attempts:
                        log.warning(f"⚠️ Muchos errores consecutivos ({failed_attempts}), saltando resto de fechas")
                        break
                    time.sleep(1.5)  # Reducido de 3 a 1.5 segundos
            
            # 📊 RESUMEN FINAL DEL HOTEL
            log.info(f"")
            log.info(f"{'='*60}")
            log.info(f"📊 RESUMEN HOTEL ID {hotel_id}")
            log.info(f"{'='*60}")
            log.info(f"🎯 Objetivo: {max_attempts} fechas")
            log.info(f"✅ Obtenidas: {successful_dates} fechas")
            log.info(f"📅 Días revisados: {days_checked}")
            log.info(f"❌ Errores: {failed_attempts}")
            log.info(f"📈 Tasa éxito: {(successful_dates/days_checked)*100:.1f}%" if days_checked > 0 else "N/A")
            log.info(f"💰 Total precios guardados: {len(results)}")
            
            if successful_dates >= max_attempts:
                log.info(f"🎉 ¡ÉXITO COMPLETO! Todas las fechas objetivo obtenidas")
                emit_scraper_log(f"🎉 HOTEL COMPLETADO: {successful_dates}/{max_attempts} fechas obtenidas", 'success', 'scraping')
            else:
                log.warning(f"⚠️ Objetivo parcial: {successful_dates}/{max_attempts} fechas")
                emit_scraper_log(f"⚠️ Objetivo parcial: {successful_dates}/{max_attempts} fechas", 'warning', 'scraping')
            
            log.info(f"{'='*60}")
        
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    log.info(f"🔧 WebDriver cerrado correctamente")
                except:
                    pass
        
        # Emitir progreso final del hotel
        if self.emit_progress:
            completion_status = 'completed_full' if successful_dates >= max_attempts else 'completed_partial'
            self.emit_progress({
                'status': f'intelligent_{completion_status}',
                'hotel_id': hotel_id,
                'total_results': len(results),
                'successful_dates': successful_dates,
                'target_dates': max_attempts,
                'days_checked': days_checked,
                'success_rate': round((successful_dates/days_checked)*100, 1) if days_checked > 0 else 0,
                'message': f'Hotel completado: {successful_dates}/{max_attempts} fechas obtenidas'
            })
        
        # 🔄 SINCRONIZACIÓN INDIVIDUAL CON OTASYNC (FUNCIONAL)
        if results and len(results) > 0 and HAVE_OTASYNC:
            log.info(f"")
            log.info(f"{'='*60}")
            log.info(f"🔄 INICIANDO SINCRONIZACIÓN CON OTASYNC")
            log.info(f"{'='*60}")
            log.info(f"📊 Total de precios a sincronizar: {len(results)}")
            
            # Emitir progreso de sincronización
            if self.emit_progress:
                self.emit_progress({
                    'status': 'otasync_sync_start',
                    'hotel_id': hotel_id,
                    'total_prices': len(results),
                    'message': f'🔄 Sincronizando {len(results)} precios con OTASync...'
                })
                
            try:
                # Inicializar cliente OTASync funcional
                otasync_client = OTASyncAPIClient()
                
                # Preparar datos para sincronización
                synced_count = 0
                failed_count = 0
                
                # Obtener configuración OTASync del hotel
                if db:
                    hotel_info = db.get_hotel_otasync_info(hotel_id)
                    if not hotel_info or not hotel_info.get('otasync_enabled', False):
                        log.warning(f"🔄 Hotel {hotel_id} no tiene OTASync habilitado, saltando sincronización")
                        return results
                    
                    property_id = hotel_info.get('otasync_property_id', 9355)  # Default test property
                    pricing_plan_id = hotel_info.get('otasync_pricing_plan_id', 26946)  # Default test plan
                    room_type_id = hotel_info.get('otasync_room_type_id', 29119)  # Default test room
                else:
                    # Usar configuración por defecto para pruebas
                    property_id = 9355
                    pricing_plan_id = 26946
                    room_type_id = 29119
                    log.warning(f"⚠️ Usando configuración por defecto OTASync")
                
                log.info(f"🏨 Configuración OTASync:")
                log.info(f"   - Property ID: {property_id}")
                log.info(f"   - Pricing Plan ID: {pricing_plan_id}")
                log.info(f"   - Room Type ID: {room_type_id}")
                
                # Sincronizar cada precio individualmente
                for i, result in enumerate(results, 1):
                    try:
                        date_str = result['checkin_date']
                        final_price = result['final_price']
                        
                        log.info(f"� [{i}/{len(results)}] Sincronizando {date_str}: ${final_price:,.0f}")
                        
                        # Crear rooms payload
                        rooms = [{
                            "id_room_types": room_type_id,
                            "value": float(final_price)
                        }]
                        
                        # Enviar actualización a OTASync
                        success = otasync_client.edit_prices(
                            property_id=property_id,
                            pricing_plan_id=pricing_plan_id,
                            date_from=date_str,
                            date_to=date_str,  # Misma fecha = actualización individual
                            rooms=rooms,
                            variation_type=0  # Precio exacto
                        )
                        
                        if success:
                            synced_count += 1
                            log.info(f"    ✅ Sincronizado exitosamente")
                            emit_scraper_log(f"✅ OTASync: {date_str} → ${final_price:,.0f}", 'success', 'otasync')
                            
                            # Marcar como sincronizado
                            result['otasync_synced'] = True
                        else:
                            failed_count += 1
                            log.error(f"    ❌ Error en sincronización")
                            emit_scraper_log(f"❌ OTASync Error: {date_str}", 'error', 'otasync')
                            
                    except Exception as e:
                        failed_count += 1
                        log.error(f"❌ Error sincronizando {result.get('checkin_date', 'fecha desconocida')}: {e}")
                        emit_scraper_log(f"❌ OTASync Error: {result.get('checkin_date', 'fecha desconocida')} - {str(e)}", 'error', 'otasync')
                
                # Resumen de sincronización
                log.info(f"")
                log.info(f"📊 RESULTADO SINCRONIZACIÓN:")
                log.info(f"✅ Sincronizados exitosamente: {synced_count}")
                log.info(f"❌ Fallidos: {failed_count}")
                log.info(f"📈 Tasa de éxito: {(synced_count/(synced_count+failed_count))*100:.1f}%" if (synced_count+failed_count) > 0 else "N/A")
                log.info(f"{'='*60}")
                
                # Emitir progreso final de sincronización
                if self.emit_progress:
                    self.emit_progress({
                        'status': 'otasync_sync_completed',
                        'hotel_id': hotel_id,
                        'synced_count': synced_count,
                        'failed_count': failed_count,
                        'total_prices': len(results),
                        'success_rate': round((synced_count/(synced_count+failed_count))*100, 1) if (synced_count+failed_count) > 0 else 0,
                        'message': f'Sincronización completada: {synced_count}/{len(results)} precios enviados a OTASync'
                    })
                    
            except Exception as e:
                log.error(f"❌ Error general en sincronización OTASync: {e}")
                emit_scraper_log(f"❌ Error en sincronización OTASync: {str(e)}", 'error', 'otasync')
        elif not HAVE_OTASYNC:
            log.warning("⚠️ OTASync API Client no disponible, saltando sincronización")
            emit_scraper_log("⚠️ OTASync API Client no disponible", 'warning', 'otasync')
        
        log.info(f"✅ Hotel ID {hotel_id} finalizado: {len(results)} resultados totales")
        
        # 🧮 VERIFICACIÓN MATEMÁTICA DE PRECIOS
        if HAVE_PRICE_VERIFIER and results:
            try:
                log.info("🧮 Iniciando verificación matemática de precios...")
                
                # Usar verificador mejorado con tolerancia
                try:
                    from enhanced_price_verification import EnhancedPriceVerificationEngine
                    verifier = EnhancedPriceVerificationEngine(tolerance=2.00)  # $2 tolerancia para redondeos
                    log.info("✅ Usando verificador mejorado con tolerancia para redondeos")
                except ImportError:
                    verifier = PriceVerificationEngine()
                    log.info("⚠️ Usando verificador estándar")
                
                verification_result = verifier.verify_scraping_results(results)
                
                # Log del resumen
                success_rate = verification_result.get('success_rate', 0)
                valid_count = verification_result.get('valid_prices', 0)
                total_count = verification_result.get('total_prices', 0)
                
                if success_rate >= 90:  # Cambiar umbral a 90% para casos con redondeos
                    log.info(f"🎉 VERIFICACIÓN EXITOSA: {valid_count}/{total_count} precios matemáticamente correctos ({success_rate:.1f}%)")
                    emit_scraper_log(f"🧮 Verificación: {valid_count}/{total_count} precios correctos ({success_rate:.1f}%)", 'success', 'verification')
                else:
                    log.warning(f"⚠️ VERIFICACIÓN PARCIAL: {valid_count}/{total_count} precios correctos ({success_rate:.1f}%)")
                    emit_scraper_log(f"⚠️ Verificación: {valid_count}/{total_count} correctos ({success_rate:.1f}%)", 'warning', 'verification')
                
                # Mostrar reporte de discrepancias si hay verificador mejorado
                if hasattr(verifier, 'generate_discrepancy_report') and valid_count < total_count:
                    discrepancy_report = verifier.generate_discrepancy_report()
                    if discrepancy_report and "No se encontraron" not in discrepancy_report:
                        log.info("📋 REPORTE DE DISCREPANCIAS:")
                        for line in discrepancy_report.split('\n'):
                            if line.strip():
                                log.info(f"   {line}")
                
                # Agregar resultado de verificación a los resultados
                for i, result in enumerate(results):
                    if i < len(verification_result.get('detailed_results', [])):
                        result['verification'] = verification_result['detailed_results'][i]
                        # Agregar flag para identificar cálculos con discrepancias menores
                        if not verification_result['detailed_results'][i]['overall_valid']:
                            result['has_minor_discrepancies'] = True
                
            except Exception as e:
                log.error(f"❌ Error en verificación matemática: {e}")
                emit_scraper_log(f"❌ Error en verificación: {str(e)}", 'error', 'verification')
        
        return results
    
    def scrape_all_hotels_intelligent(self) -> Dict:
        """
        🏨 SCRAPER MASIVO DE TODOS LOS HOTELES - FLUJO COMPLETO
        ======================================================
        
        PROCESO POR CADA HOTEL:
        1. 🎯 Obtener exactamente 20 fechas con precios
        2. 📊 Aplicar margen configurado por hotel
        3. 💾 Guardar en base de datos con timestamp
        4. 🔄 Sincronizar automáticamente con OTASync
        5. ➡️ Continuar al siguiente hotel
        
        CARACTERÍSTICAS:
        - Logging detallado por cada paso
        - Manejo de errores robusto
        - Pausas inteligentes entre hoteles
        - Progreso en tiempo real vía WebSocket
        - Resumen estadístico completo
        """
        log.info("")
        log.info("🏨"*30)
        log.info("🤖 INICIANDO SCRAPING MASIVO INTELIGENTE")
        log.info("🏨"*30)
        log.info("")
        
        # Inicializar DB
        db_path = os.environ.get('DB_PATH')
        if db_path:
            db = DatabaseManager(db_path=db_path)
            log.info(f"🗄️ Usando base de datos: {db_path}")
        else:
            db = DatabaseManager()
            log.info(f"🗄️ Usando base de datos por defecto")

        # Obtener hoteles configurados
        hotels = db.get_all_hotels()
        if not hotels:
            log.error("❌ No hay hoteles configurados en la base de datos")
            return {"error": "No hotels found", "success": False}
        
        log.info(f"🏨 HOTELES ENCONTRADOS: {len(hotels)}")
        for i, hotel in enumerate(hotels, 1):
            log.info(f"  {i}. {hotel['name']} (ID: {hotel['id']})")
        
        # Variables de control
        results = {}
        total_successful_dates = 0
        total_hotels_processed = 0
        hotels_with_full_success = 0
        processing_errors = []
        
        # Emitir progreso inicial
        if self.emit_progress:
            self.emit_progress({
                'status': 'intelligent_start_all',
                'total_hotels': len(hotels),
                'target_dates_per_hotel': 20,
                'total_target_dates': len(hotels) * 20,
                'message': f'🎯 Iniciando scraping masivo: {len(hotels)} hoteles × 20 fechas = {len(hotels) * 20} precios objetivo'
            })
        
        # 🏨 PROCESAR CADA HOTEL SECUENCIALMENTE
        for i, hotel in enumerate(hotels, 1):
            hotel_start_time = datetime.now()
            
            log.info(f"")
            log.info(f"🏨" + "="*80)
            log.info(f"🏨 HOTEL {i}/{len(hotels)}: {hotel['name']}")
            log.info(f"🏨 ID: {hotel['id']} | URL: {hotel['url'][:60]}...")
            log.info(f"🏨" + "="*80)
            
            # Emitir progreso por hotel
            if self.emit_progress:
                self.emit_progress({
                    'status': 'intelligent_hotel_start',
                    'hotel_number': i,
                    'total_hotels': len(hotels),
                    'hotel_name': hotel['name'],
                    'hotel_id': hotel['id'],
                    'hotels_completed': total_hotels_processed,
                    'total_dates_so_far': total_successful_dates
                })
            
            try:
                # 🎯 SCRAPING DEL HOTEL (20 fechas objetivo)
                log.info(f"🎯 Objetivo: 20 fechas con precios válidos")
                hotel_results = self.scrape_hotel_intelligent(
                    hotel['url'], 
                    hotel['id'], 
                    max_attempts=20
                )
                
                # 📊 ANÁLISIS DE RESULTADOS
                dates_obtained = len(hotel_results)
                otasync_synced_count = sum(1 for r in hotel_results if r.get('otasync_synced', False))
                
                # Guardar estadísticas del hotel
                hotel_stats = {
                    'dates_obtained': dates_obtained,
                    'dates_target': 20,
                    'success_rate': (dates_obtained / 20) * 100,
                    'otasync_synced': otasync_synced_count,
                    'processing_time': (datetime.now() - hotel_start_time).total_seconds(),
                    'results': hotel_results
                }
                
                results[hotel['name']] = hotel_stats
                total_successful_dates += dates_obtained
                total_hotels_processed += 1
                
                # Verificar éxito completo
                if dates_obtained >= 20:
                    hotels_with_full_success += 1
                    log.info(f"🎉 ¡ÉXITO COMPLETO! {dates_obtained}/20 fechas obtenidas")
                    emit_scraper_log(f"🎉 {hotel['name']}: ÉXITO COMPLETO - {dates_obtained}/20 fechas", 'success', 'hotel_completed')
                else:
                    log.warning(f"⚠️ Éxito parcial: {dates_obtained}/20 fechas obtenidas")
                    emit_scraper_log(f"⚠️ {hotel['name']}: Parcial - {dates_obtained}/20 fechas", 'warning', 'hotel_completed')
                
                # Mostrar resumen del hotel
                processing_time = hotel_stats['processing_time']
                log.info(f"")
                log.info(f"📊 RESUMEN HOTEL {i}: {hotel['name']}")
                log.info(f"   ✅ Fechas obtenidas: {dates_obtained}/20 ({hotel_stats['success_rate']:.1f}%)")
                log.info(f"   🔄 Sincronizadas OTASync: {otasync_synced_count}")
                log.info(f"   ⏱️ Tiempo procesamiento: {processing_time:.1f}s")
                
                # Emitir progreso de hotel completado
                if self.emit_progress:
                    self.emit_progress({
                        'status': 'intelligent_hotel_completed',
                        'hotel_name': hotel['name'],
                        'hotel_id': hotel['id'],
                        'hotel_number': i,
                        'total_hotels': len(hotels),
                        'dates_obtained': dates_obtained,
                        'dates_target': 20,
                        'success_rate': hotel_stats['success_rate'],
                        'otasync_synced': otasync_synced_count,
                        'processing_time': processing_time,
                        'total_dates_so_far': total_successful_dates,
                        'hotels_completed': total_hotels_processed
                    })
                
                # ⏳ PAUSA ENTRE HOTELES (excepto el último)
                if i < len(hotels):
                    wait_time = random.uniform(30, 60)  # Pausa más larga entre hoteles
                    log.info(f"")
                    log.info(f"⏳ Esperando {wait_time:.1f}s antes del siguiente hotel...")
                    log.info(f"   📈 Progreso general: {i}/{len(hotels)} hoteles ({total_successful_dates} fechas totales)")
                    
                    # Mostrar tiempo estimado restante
                    avg_time_per_hotel = (datetime.now() - hotel_start_time).total_seconds()
                    estimated_remaining = avg_time_per_hotel * (len(hotels) - i)
                    log.info(f"   ⏰ Tiempo estimado restante: {estimated_remaining/60:.1f} minutos")
                    
                    time.sleep(wait_time)
                
            except Exception as e:
                error_msg = f"Error procesando hotel {hotel['name']}: {str(e)}"
                log.error(f"❌ {error_msg}")
                emit_scraper_log(f"❌ {hotel['name']}: Error - {str(e)}", 'error', 'hotel_error')
                
                processing_errors.append({
                    'hotel_name': hotel['name'],
                    'hotel_id': hotel['id'],
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                
                results[hotel['name']] = {"error": str(e), "success": False}
                total_hotels_processed += 1
        
        # 🎉 RESUMEN FINAL COMPLETO
        processing_end_time = datetime.now()
        total_processing_time = (processing_end_time - datetime.now()).total_seconds()  # Aproximación
        
        log.info(f"")
        log.info(f"🎉" + "="*80)
        log.info(f"🎉 SCRAPING MASIVO COMPLETADO")
        log.info(f"🎉" + "="*80)
        log.info(f"")
        log.info(f"📊 ESTADÍSTICAS FINALES:")
        log.info(f"   🏨 Hoteles procesados: {total_hotels_processed}/{len(hotels)}")
        log.info(f"   ✅ Hoteles con éxito completo: {hotels_with_full_success}")
        log.info(f"   📅 Total fechas obtenidas: {total_successful_dates}")
        log.info(f"   🎯 Total fechas objetivo: {len(hotels) * 20}")
        log.info(f"   📈 Tasa éxito general: {(total_successful_dates/(len(hotels)*20))*100:.1f}%")
        log.info(f"   ❌ Errores: {len(processing_errors)}")
        
        # Total de sincronizaciones OTASync
        total_otasync_synced = sum(
            r.get('otasync_synced', 0) for r in results.values() 
            if isinstance(r, dict) and 'otasync_synced' in r
        )
        log.info(f"   🔄 Total sincronizado OTASync: {total_otasync_synced}")
        
        if processing_errors:
            log.info(f"")
            log.info(f"❌ ERRORES ENCONTRADOS:")
            for error in processing_errors:
                log.info(f"   • {error['hotel_name']}: {error['error']}")
        
        # Emitir progreso final
        final_success_rate = (total_successful_dates / (len(hotels) * 20)) * 100 if hotels else 0
        
        if self.emit_progress:
            self.emit_progress({
                'status': 'intelligent_all_completed',
                'total_hotels': len(hotels),
                'hotels_processed': total_hotels_processed,
                'hotels_full_success': hotels_with_full_success,
                'total_dates_obtained': total_successful_dates,
                'total_dates_target': len(hotels) * 20,
                'success_rate': final_success_rate,
                'total_otasync_synced': total_otasync_synced,
                'processing_errors': len(processing_errors),
                'message': f'🎉 Scraping masivo completado: {total_successful_dates} precios de {len(hotels)} hoteles'
            })
        
        log.info(f"")
        log.info(f"🎉 ¡PROCESO COMPLETADO EXITOSAMENTE!")
        log.info(f"🎉" + "="*80)
        
        return {
            'success': True,
            'total_hotels': len(hotels),
            'hotels_processed': total_hotels_processed,
            'hotels_full_success': hotels_with_full_success,
            'total_dates_obtained': total_successful_dates,
            'total_dates_target': len(hotels) * 20,
            'success_rate': final_success_rate,
            'total_otasync_synced': total_otasync_synced,
            'processing_errors': processing_errors,
            'results': results
        }

# Función para integración con Flask (similar a restored_scraper)
def scrape_intelligent_for_flask(hotel_id=None, max_attempts=DEFAULT_SCRAPING_DAYS, emit_progress=None):
    """
    Función optimizada para usar desde Flask con WebSocket updates
    Usa el método inteligente de búsqueda de fechas
    """
    if not HAVE_SELENIUM:
        return {'success': False, 'error': 'Selenium no está disponible en este entorno'}

    try:
        scraper = IntelligentScraper(headless=True)
        
        # Asignar la función de progreso al scraper
        if emit_progress:
            scraper.emit_progress = emit_progress
        
        if hotel_id:
            # Scrapear hotel específico
            # Priorizar DB_PATH de variable de entorno, luego usar Django DB por defecto
            db_path = os.environ.get('DB_PATH')
            if not db_path:
                # Usar la base de datos de Django por defecto
                django_db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
                if os.path.exists(django_db_path):
                    db_path = django_db_path
                    
            if db_path:
                db = DatabaseManager(db_path=db_path)
                log.info(f"🔍 FLASK-SCRAPER: Using database: {db_path}")
            else:
                db = DatabaseManager()
                log.info(f"🔍 FLASK-SCRAPER: Using default database")
            
            # Try to get hotel from database
            hotel = db.get_hotel_by_id(hotel_id)
            if not hotel:
                # Try direct SQL query as fallback
                log.warning(f"🔍 FLASK-SCRAPER: get_hotel_by_id failed for hotel {hotel_id}, trying direct SQL")
                try:
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT id, name, url, price_percent FROM hotels_hotel WHERE id = ?", (hotel_id,))
                        row = cursor.fetchone()
                        if row:
                            hotel = {
                                'id': row[0],
                                'name': row[1],
                                'url': row[2],
                                'price_percent': row[3] or 0.0
                            }
                            log.info(f"🔍 FLASK-SCRAPER: Found hotel via direct SQL: {hotel}")
                        else:
                            return {"error": f"Hotel con ID {hotel_id} no encontrado en la base de datos"}
                except Exception as e:
                    return {"error": f"Error accessing database for hotel {hotel_id}: {str(e)}"}
            
            if not hotel:
                return {"error": f"Hotel con ID {hotel_id} no encontrado"}
            
            results = scraper.scrape_hotel_intelligent(
                hotel['url'], 
                hotel['id'],
                max_attempts=max_attempts
            )
            
            return {
                'success': True,
                'total_prices': len(results),
                'hotel_name': hotel['name'],
                'results': results
            }
        else:
            # Scrapear todos los hoteles
            return scraper.scrape_all_hotels_intelligent()
            
    except Exception as e:
        return {"error": f"Error en scraping inteligente: {str(e)}"}

def main():
    """Función principal para probar el scraper inteligente"""
    print("🤖 Scraper Inteligente con Detección de Disponibilidad")
    print("=" * 60)
    
    # Procesar argumentos de línea de comandos
    import argparse
    parser = argparse.ArgumentParser(description='Scraper Inteligente con soporte para porcentajes')
    parser.add_argument('--with-percentage-fix', action='store_true', 
                      help='Usar la nueva implementación de porcentajes')
    parser.add_argument('--hotel-id', type=int, help='ID del hotel a scrapear (opcional)')
    parser.add_argument('--headless', action='store_true', default=True,
                      help='Ejecutar en modo headless (por defecto)')
    args = parser.parse_args()
    
    if args.with_percentage_fix:
        print("✅ Usando implementación corregida de porcentajes")
        # Verificar que el módulo está disponible
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from actualizar_precios_con_porcentaje import sync_hotel_price_with_percentage
            print("✅ Módulo de porcentajes cargado correctamente")
        except ImportError:
            print("⚠️ No se pudo cargar el módulo de porcentajes, usando implementación estándar")
    
    scraper = IntelligentScraper(headless=args.headless)
    
    try:
        if args.hotel_id:
            print(f"🏨 Scraping para hotel específico: {args.hotel_id}")
            hotel = {'id': args.hotel_id}
            results = scraper.scrape_hotel_intelligent(hotel['id'])
        else:
            print("🏨 Scraping para todos los hoteles")
            results = scraper.scrape_all_hotels_intelligent()
        
        print("\n📊 RESUMEN FINAL:")
        print("-" * 30)
        
        if 'results' in results:
            for hotel_name, hotel_results in results['results'].items():
                print(f"\n🏨 {hotel_name}:")
                if isinstance(hotel_results, list) and hotel_results:
                    for result in hotel_results[:5]:  # Mostrar solo los primeros 5
                        print(f"   📅 {result['checkin_date']} - {result['price_text']}")
                    if len(hotel_results) > 5:
                        print(f"   ... y {len(hotel_results) - 5} más")
                else:
                    print("   ❌ Sin resultados")
                
    except KeyboardInterrupt:
        print("\n⏹️ Scraping detenido por el usuario")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
