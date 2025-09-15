"""
Socket Manager para comunicación en tiempo real
Versión simplificada para el proyecto limpio
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SocketManager:
    """
    Manager simplificado para comunicación en tiempo real
    Versión autocontenida sin dependencias externas
    """
    
    def __init__(self):
        self.connections = []
        self.rooms = {}
        self.status = "initialized"
        
    def add_connection(self, connection_id, room=None):
        """
        Agregar nueva conexión
        
        Args:
            connection_id (str): ID único de la conexión
            room (str, optional): Sala a la que pertenece la conexión
        """
        try:
            connection_info = {
                'id': connection_id,
                'room': room,
                'connected_at': datetime.now(),
                'status': 'active'
            }
            
            self.connections.append(connection_info)
            
            if room:
                if room not in self.rooms:
                    self.rooms[room] = []
                self.rooms[room].append(connection_id)
            
            logger.info(f"Conexión agregada: {connection_id} en sala {room}")
            return True
            
        except Exception as e:
            logger.error(f"Error agregando conexión {connection_id}: {e}")
            return False
    
    def remove_connection(self, connection_id):
        """
        Remover conexión existente
        
        Args:
            connection_id (str): ID de la conexión a remover
        """
        try:
            # Remover de connections
            self.connections = [conn for conn in self.connections if conn['id'] != connection_id]
            
            # Remover de rooms
            for room, connections in self.rooms.items():
                if connection_id in connections:
                    connections.remove(connection_id)
            
            logger.info(f"Conexión removida: {connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removiendo conexión {connection_id}: {e}")
            return False
    
    def send_message(self, connection_id, message_type, data):
        """
        Enviar mensaje a conexión específica
        
        Args:
            connection_id (str): ID de la conexión destino
            message_type (str): Tipo de mensaje
            data (dict): Datos del mensaje
        """
        try:
            message = {
                'type': message_type,
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'target': connection_id
            }
            
            # En una implementación real, aquí se enviaría por WebSocket
            logger.info(f"Mensaje enviado a {connection_id}: {message_type}")
            return message
            
        except Exception as e:
            logger.error(f"Error enviando mensaje a {connection_id}: {e}")
            return None
    
    def broadcast_to_room(self, room, message_type, data):
        """
        Enviar mensaje a todas las conexiones de una sala
        
        Args:
            room (str): Nombre de la sala
            message_type (str): Tipo de mensaje
            data (dict): Datos del mensaje
        """
        try:
            if room not in self.rooms:
                logger.warning(f"Sala {room} no existe")
                return False
            
            message = {
                'type': message_type,
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'room': room
            }
            
            sent_count = 0
            for connection_id in self.rooms[room]:
                if self.send_message(connection_id, message_type, data):
                    sent_count += 1
            
            logger.info(f"Mensaje broadcasted a sala {room}: {sent_count} conexiones")
            return True
            
        except Exception as e:
            logger.error(f"Error broadcasting a sala {room}: {e}")
            return False
    
    def get_room_connections(self, room):
        """
        Obtener conexiones activas de una sala
        
        Args:
            room (str): Nombre de la sala
            
        Returns:
            list: Lista de IDs de conexiones
        """
        return self.rooms.get(room, [])
    
    def get_connection_count(self):
        """
        Obtener número total de conexiones activas
        
        Returns:
            int: Número de conexiones
        """
        return len(self.connections)
    
    def get_status(self):
        """
        Obtener estado del socket manager
        
        Returns:
            dict: Estado actual
        """
        return {
            'status': self.status,
            'total_connections': len(self.connections),
            'total_rooms': len(self.rooms),
            'rooms': {room: len(connections) for room, connections in self.rooms.items()}
        }

# Instancia global del socket manager
socket_manager = SocketManager()

def emit_scraping_progress(hotel_id, progress_data):
    """
    Emitir progreso del scraping para un hotel específico
    
    Args:
        hotel_id (int): ID del hotel
        progress_data (dict): Datos del progreso
    """
    try:
        room = f"hotel_{hotel_id}"
        message_type = "scraping_progress"
        
        data = {
            'hotel_id': hotel_id,
            'progress': progress_data.get('progress', 0),
            'status': progress_data.get('status', 'unknown'),
            'message': progress_data.get('message', ''),
            'timestamp': datetime.now().isoformat()
        }
        
        socket_manager.broadcast_to_room(room, message_type, data)
        return True
        
    except Exception as e:
        logger.error(f"Error emitiendo progreso de scraping para hotel {hotel_id}: {e}")
        return False

def emit_scraping_complete(hotel_id, results):
    """
    Emitir finalización del scraping
    
    Args:
        hotel_id (int): ID del hotel
        results (dict): Resultados del scraping
    """
    try:
        room = f"hotel_{hotel_id}"
        message_type = "scraping_complete"
        
        data = {
            'hotel_id': hotel_id,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
        
        socket_manager.broadcast_to_room(room, message_type, data)
        return True
        
    except Exception as e:
        logger.error(f"Error emitiendo finalización de scraping para hotel {hotel_id}: {e}")
        return False

def emit_scraping_error(hotel_id, error_message):
    """
    Emitir error en el scraping
    
    Args:
        hotel_id (int): ID del hotel
        error_message (str): Mensaje de error
    """
    try:
        room = f"hotel_{hotel_id}"
        message_type = "scraping_error"
        
        data = {
            'hotel_id': hotel_id,
            'error': error_message,
            'timestamp': datetime.now().isoformat()
        }
        
        socket_manager.broadcast_to_room(room, message_type, data)
        return True
        
    except Exception as e:
        logger.error(f"Error emitiendo error de scraping para hotel {hotel_id}: {e}")
        return False

def emit_log_message(message, level='info', category='general'):
    """
    Emitir mensaje de log general
    
    Args:
        message (str): Mensaje de log
        level (str): Nivel de log (info, warning, error)
        category (str): Categoría del mensaje (general, scraping, database, otasync, etc.)
    """
    try:
        message_type = "log_message"
        
        data = {
            'message': message,
            'level': level,
            'category': category,
            'timestamp': datetime.now().isoformat()
        }
        
        # Enviar a una sala general de logs
        socket_manager.broadcast_to_room('logs', message_type, data)
        logger.info(f"Log message emitted: {message}")
        return True
        
    except Exception as e:
        logger.error(f"Error emitiendo mensaje de log: {e}")
        return False
