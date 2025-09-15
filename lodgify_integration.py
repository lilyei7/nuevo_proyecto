"""
Lodgify Integration Stub
Versión simplificada para evitar errores de importación
"""

def get_lodgify_integration():
    """
    Stub para integración con Lodgify
    Retorna None porque ya no usamos Lodgify
    """
    return None

def sync_scraped_price_to_lodgify(hotel_id, price_data):
    """
    Stub para sincronización de precios con Lodgify
    No hace nada porque ahora usamos OTASync
    
    Args:
        hotel_id: ID del hotel
        price_data: Datos de precios
        
    Returns:
        dict: Resultado vacío
    """
    return {
        'success': False,
        'message': 'Lodgify integration disabled - Using OTASync instead',
        'lodgify_disabled': True
    }

class LodgifyIntegration:
    """
    Clase stub para mantener compatibilidad
    """
    
    def __init__(self):
        self.enabled = False
        self.message = "Lodgify integration disabled - Using OTASync"
    
    def sync_price(self, hotel_id, price_data):
        return sync_scraped_price_to_lodgify(hotel_id, price_data)
    
    def is_enabled(self):
        return False
