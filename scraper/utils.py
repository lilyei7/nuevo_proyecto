"""
Utilidades para scraping de hoteles
Versión autocontenida - no depende de archivos externos
"""

import re
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

def parse_booking_url(url):
    """
    Parsear URL de Booking.com para extraer información del hotel
    
    Args:
        url (str): URL de Booking.com
        
    Returns:
        dict: Información extraída de la URL
    """
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Extraer información básica
        info = {
            'domain': parsed.netloc,
            'path': parsed.path,
            'checkin': query_params.get('checkin', [None])[0],
            'checkout': query_params.get('checkout', [None])[0],
            'adults': query_params.get('sb_adults', [None])[0],
            'children': query_params.get('sb_children', [None])[0],
            'rooms': query_params.get('sb_rooms', [None])[0]
        }
        
        # Extraer ID del hotel desde la URL si está disponible
        hotel_match = re.search(r'/hotel/([a-z]{2})/([^/?]+)', parsed.path)
        if hotel_match:
            info['country'] = hotel_match.group(1)
            info['hotel_slug'] = hotel_match.group(2)
        
        return info
        
    except Exception as e:
        print(f"Error parseando URL de Booking: {e}")
        return {}

def build_url_from_template(template, checkin_date, checkout_date, **kwargs):
    """
    Construir URL desde un template con fechas específicas
    
    Args:
        template (str): Template de URL base o URL completa
        checkin_date (date): Fecha de check-in
        checkout_date (date): Fecha de check-out
        **kwargs: Parámetros adicionales
        
    Returns:
        str: URL construida con las fechas
    """
    try:
        # Si template es una URL completa, modificarla con nuevas fechas
        if isinstance(template, str) and 'booking.com' in template:
            base_url = template
            
            # Reemplazar fechas existentes o agregar nuevas
            checkin_str = checkin_date.strftime('%Y-%m-%d') if hasattr(checkin_date, 'strftime') else str(checkin_date)
            checkout_str = checkout_date.strftime('%Y-%m-%d') if hasattr(checkout_date, 'strftime') else str(checkout_date)
            
            # Si ya tiene parámetros de fecha, reemplazarlos
            if 'checkin=' in base_url and 'checkout=' in base_url:
                # Usar regex para reemplazar fechas existentes
                base_url = re.sub(r'checkin=[^&]*', f'checkin={checkin_str}', base_url)
                base_url = re.sub(r'checkout=[^&]*', f'checkout={checkout_str}', base_url)
            else:
                # Agregar parámetros de fecha
                separator = '&' if '?' in base_url else '?'
                base_url += f'{separator}checkin={checkin_str}&checkout={checkout_str}'
            
            return base_url
        
        # Si es un template con placeholders, usar el método original
        kwargs.update({
            'checkin': checkin_date.strftime('%Y-%m-%d') if hasattr(checkin_date, 'strftime') else str(checkin_date),
            'checkout': checkout_date.strftime('%Y-%m-%d') if hasattr(checkout_date, 'strftime') else str(checkout_date)
        })
        
        # Valores por defecto para huéspedes
        if 'adults' not in kwargs:
            kwargs['adults'] = '2'
        
        if 'children' not in kwargs:
            kwargs['children'] = '0'
            
        if 'rooms' not in kwargs:
            kwargs['rooms'] = '1'
        
        # Reemplazar placeholders en el template
        url = template.format(**kwargs)
        return url
        
    except Exception as e:
        print(f"Error construyendo URL desde template: {e}")
        return template

def extract_hotel_info_from_html(html_content):
    """
    Extraer información básica del hotel desde contenido HTML
    
    Args:
        html_content (str): Contenido HTML de la página del hotel
        
    Returns:
        dict: Información extraída del hotel
    """
    try:
        info = {
            'name': None,
            'rating': None,
            'price': None,
            'currency': None,
            'address': None,
            'description': None
        }
        
        # Extraer nombre del hotel
        name_patterns = [
            r'<h1[^>]*>([^<]+)</h1>',
            r'<title>([^<]*?)\s*[-|]\s*Booking\.com</title>',
            r'property_name["\']:\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                info['name'] = match.group(1).strip()
                break
        
        # Extraer precio
        price_patterns = [
            r'[\$€£¥₹]\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'([0-9,]+(?:\.[0-9]{2})?)\s*[\$€£¥₹]',
            r'price["\']:\s*["\']?([0-9,]+(?:\.[0-9]{2})?)'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, html_content)
            if match:
                info['price'] = float(match.group(1).replace(',', ''))
                break
        
        # Extraer rating
        rating_patterns = [
            r'rating["\']:\s*["\']?([0-9]+\.?[0-9]*)',
            r'([0-9]+\.?[0-9]*)\s*out\s*of\s*[0-9]+',
            r'star_rating["\']:\s*["\']?([0-9]+)'
        ]
        
        for pattern in rating_patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                info['rating'] = float(match.group(1))
                break
        
        return info
        
    except Exception as e:
        print(f"Error extrayendo información del HTML: {e}")
        return {}

def validate_hotel_data(hotel_data):
    """
    Validar datos básicos de un hotel
    
    Args:
        hotel_data (dict): Datos del hotel para validar
        
    Returns:
        bool: True si los datos son válidos
    """
    try:
        required_fields = ['name', 'url']
        
        for field in required_fields:
            if field not in hotel_data or not hotel_data[field]:
                return False
        
        # Validar URL
        parsed_url = urlparse(hotel_data['url'])
        if not parsed_url.scheme or not parsed_url.netloc:
            return False
        
        return True
        
    except Exception as e:
        print(f"Error validando datos del hotel: {e}")
        return False

def clean_hotel_name(name):
    """
    Limpiar nombre del hotel removiendo caracteres especiales
    
    Args:
        name (str): Nombre original del hotel
        
    Returns:
        str: Nombre limpio
    """
    if not name:
        return ""
    
    # Remover caracteres especiales y espacios extra
    clean_name = re.sub(r'[^\w\s-]', '', name)
    clean_name = re.sub(r'\s+', ' ', clean_name)
    return clean_name.strip()

def format_price(price, currency='USD'):
    """
    Formatear precio con moneda
    
    Args:
        price (float): Precio numérico
        currency (str): Código de moneda
        
    Returns:
        str: Precio formateado
    """
    if price is None:
        return "N/A"
    
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'COP': '$'
    }
    
    symbol = currency_symbols.get(currency, currency)
    return f"{symbol} {price:,.2f}"
