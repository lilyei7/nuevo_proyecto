#!/usr/bin/env python3
"""
OTASync Properties Discovery - Método Inteligente
Basado en análisis profundo de backups y patrones de funcionamiento
"""

import sys
import os
import requests
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.otasync_client import OTASyncClient


class OTASyncPropertiesDiscovery:
    """
    Cliente especializado en descubrir propiedades de OTASync
    Usa múltiples estrategias basándose en la evidencia disponible
    """
    
    def __init__(self):
        self.base_url = "https://app.otasync.me"
        self.session = requests.Session()
        self.main_client = OTASyncClient()
        
        # Cargar credenciales
        self._load_credentials()
        
        # IDs de propiedades conocidas de los backups
        self.known_property_ids = [9355]  # Extraído de los backups
        
        print(f"🔍 OTASync Properties Discovery iniciado")
    
    def _load_credentials(self):
        """Cargar credenciales desde kunas"""
        credentials_path = "/home/gordon/Escritorio/scraping/nuevo_proyecto/kunas/credentials.txt"
        
        creds = {}
        with open(credentials_path, 'r') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    creds[k] = v
        
        self.token = creds['token']
        self.username = creds['username']
        self.password = creds['password']
        self.pkey = None
    
    def authenticate(self) -> bool:
        """Autenticar y obtener pkey"""
        try:
            self.pkey, response = self.main_client.login(self.token, self.username, self.password)
            if self.pkey:
                print(f"✅ Autenticado - pkey: {self.pkey[:10]}...")
                return True
            return False
        except Exception as e:
            print(f"❌ Error autenticación: {e}")
            return False
    
    def discover_properties_via_calendar_scan(self) -> List[Dict]:
        """
        Método 1: Descubrir propiedades probando IDs conocidos y obteniendo su calendario
        Este método funciona porque el calendario devuelve información de la propiedad
        """
        print("\n🔍 MÉTODO 1: Discovery via Calendar Scan")
        
        if not self.pkey:
            if not self.authenticate():
                return []
        
        discovered_properties = []
        
        # Expandir rango de IDs para probar (basándose en 9355)
        id_ranges = [
            range(9350, 9360),  # Rango cercano al conocido
            range(9300, 9400, 10),  # Saltos de 10
            range(9000, 10000, 50),  # Saltos de 50
            range(8000, 12000, 100), # Saltos de 100
        ]
        
        tested_ids = set()
        
        for id_range in id_ranges:
            for prop_id in id_range:
                if prop_id in tested_ids:
                    continue
                    
                tested_ids.add(prop_id)
                
                try:
                    print(f"   Probando ID {prop_id}...", end=" ")
                    
                    # Intentar obtener calendar para este ID
                    calendar_response = self.main_client.get_calendar(
                        self.token, self.pkey, prop_id,
                        date=datetime.now().strftime('%Y-%m-%d'),
                        days=3
                    )
                    
                    if calendar_response and calendar_response.status_code == 200:
                        try:
                            calendar_data = calendar_response.json()
                            
                            # Verificar si tiene estructura válida de propiedad
                            if 'property' in calendar_data and 'filters' in calendar_data:
                                property_info = calendar_data['property']
                                filters = calendar_data['filters']
                                
                                # Extraer información de la propiedad
                                property_data = {
                                    'id_properties': prop_id,
                                    'name': property_info.get('name', f'Property_{prop_id}'),
                                    'currency': property_info.get('currency', 'Unknown'),
                                    'discovered_via': 'calendar_scan',
                                    'filters': filters,
                                    'room_types': calendar_data.get('room_types', []),
                                    'raw_calendar_data': calendar_data
                                }
                                
                                discovered_properties.append(property_data)
                                print(f"✅ ENCONTRADA: {property_info.get('name', 'Sin nombre')}")
                                
                                # Si encontramos propiedades válidas, podemos reducir el rango
                                if len(discovered_properties) >= 5:
                                    print(f"   Encontradas {len(discovered_properties)} propiedades, reduciendo búsqueda...")
                                    break
                            else:
                                print("❌ Estructura inválida")
                        except json.JSONDecodeError:
                            print("❌ JSON inválido")
                    elif calendar_response and calendar_response.status_code == 403:
                        print("🚫 Forbidden")
                    elif calendar_response and calendar_response.status_code == 404:
                        print("❌ No existe")
                    else:
                        status = calendar_response.status_code if calendar_response else 'No response'
                        print(f"❌ Status {status}")
                        
                except Exception as e:
                    print(f"💥 Error: {e}")
                
                # Pausa para evitar rate limiting
                import time
                time.sleep(0.1)
            
            if discovered_properties:
                break  # Si encontramos propiedades, no necesitamos seguir con rangos más amplios
        
        print(f"📊 Método 1 completado: {len(discovered_properties)} propiedades encontradas")
        return discovered_properties
    
    def discover_properties_via_web_scraping(self) -> List[Dict]:
        """
        Método 2: Descubrir propiedades analizando las respuestas HTML de la web
        """
        print("\n🔍 MÉTODO 2: Discovery via Web Scraping")
        
        if not self.pkey:
            if not self.authenticate():
                return []
        
        discovered_properties = []
        
        # URLs que podrían contener información de propiedades
        web_endpoints = [
            "/dashboard",
            "/properties",
            "/calendar",
            "/",
            "/api/dashboard",
            "/api/user/properties",
            "/account/properties"
        ]
        
        for endpoint in web_endpoints:
            try:
                print(f"   Analizando {endpoint}...", end=" ")
                
                # Hacer request con headers de autenticación
                headers = {
                    'Authorization': f'Bearer {self.pkey}',
                    'Cookie': f'pkey={self.pkey}',
                    'User-Agent': 'Mozilla/5.0 (compatible; OTASync-Client/1.0)'
                }
                
                response = self.session.get(f"{self.base_url}{endpoint}", headers=headers)
                
                if response.status_code == 200:
                    # Buscar patrones de propiedades en el HTML
                    property_patterns = [
                        r'"id_properties":\s*(\d+)',
                        r'"property_id":\s*(\d+)',
                        r'property[_-]?id["\']?\s*:\s*["\']?(\d+)',
                        r'id["\']?\s*:\s*["\']?(\d+)["\']?\s*,\s*["\']?name["\']?\s*:\s*["\']([^"\']+)',
                        r'properties\[(\d+)\]',
                        r'property_(\d+)',
                    ]
                    
                    found_ids = set()
                    found_names = {}
                    
                    for pattern in property_patterns:
                        matches = re.finditer(pattern, response.text, re.IGNORECASE)
                        for match in matches:
                            try:
                                prop_id = int(match.group(1))
                                found_ids.add(prop_id)
                                
                                # Si el patrón incluye nombre, extraerlo
                                if len(match.groups()) > 1:
                                    found_names[prop_id] = match.group(2)
                            except:
                                continue
                    
                    if found_ids:
                        print(f"✅ {len(found_ids)} IDs encontrados")
                        
                        # Verificar cada ID encontrado
                        for prop_id in found_ids:
                            if prop_id not in [p['id_properties'] for p in discovered_properties]:
                                # Verificar que el ID es válido obteniendo su calendario
                                cal_data = self._verify_property_id(prop_id)
                                if cal_data:
                                    property_data = {
                                        'id_properties': prop_id,
                                        'name': found_names.get(prop_id, f'Property_{prop_id}'),
                                        'discovered_via': f'web_scraping_{endpoint}',
                                        'calendar_data': cal_data
                                    }
                                    discovered_properties.append(property_data)
                    else:
                        print("❌ No IDs encontrados")
                else:
                    print(f"❌ Status {response.status_code}")
                    
            except Exception as e:
                print(f"💥 Error: {e}")
        
        print(f"📊 Método 2 completado: {len(discovered_properties)} propiedades encontradas")
        return discovered_properties
    
    def _verify_property_id(self, prop_id: int) -> Optional[Dict]:
        """Verificar que un ID de propiedad es válido obteniendo su calendario"""
        try:
            calendar_response = self.main_client.get_calendar(
                self.token, self.pkey, prop_id,
                date=datetime.now().strftime('%Y-%m-%d'),
                days=1
            )
            
            if calendar_response and calendar_response.status_code == 200:
                try:
                    return calendar_response.json()
                except:
                    return None
            return None
        except:
            return None
    
    def discover_properties_via_backup_analysis(self) -> List[Dict]:
        """
        Método 3: Analizar backups existentes para extraer información de propiedades
        """
        print("\n🔍 MÉTODO 3: Discovery via Backup Analysis")
        
        discovered_properties = []
        backups_dir = "/home/gordon/Escritorio/scraping/kunas/backups"
        
        if not os.path.exists(backups_dir):
            print("❌ Directorio de backups no encontrado")
            return []
        
        # Analizar archivos de backup
        for filename in os.listdir(backups_dir):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(backups_dir, filename)
                    
                    with open(filepath, 'r') as f:
                        backup_data = json.load(f)
                    
                    # Buscar información de propiedades en diferentes estructuras
                    property_info = self._extract_property_from_backup(backup_data, filename)
                    
                    if property_info:
                        # Verificar que la propiedad sigue activa
                        if self._verify_property_id(property_info['id_properties']):
                            property_info['discovered_via'] = f'backup_analysis_{filename}'
                            discovered_properties.append(property_info)
                            print(f"   ✅ Extraída de {filename}: {property_info['name']}")
                        else:
                            print(f"   ⚠️  Propiedad de {filename} ya no activa")
                    
                except Exception as e:
                    print(f"   ❌ Error analizando {filename}: {e}")
        
        print(f"📊 Método 3 completado: {len(discovered_properties)} propiedades encontradas")
        return discovered_properties
    
    def _extract_property_from_backup(self, backup_data: Dict, filename: str) -> Optional[Dict]:
        """Extraer información de propiedad de un archivo de backup"""
        try:
            # Patrón 1: Calendar backup
            if 'property' in backup_data:
                prop_info = backup_data['property']
                filters = backup_data.get('filters', {})
                
                return {
                    'id_properties': filters.get('id_properties'),
                    'name': prop_info.get('name', 'Unknown'),
                    'currency': prop_info.get('currency', 'Unknown'),
                    'room_types': backup_data.get('room_types', []),
                    'filters': filters
                }
            
            # Patrón 2: Response backup
            if 'body' in backup_data:
                # Intentar extraer ID del filename
                id_match = re.search(r'(\d+)', filename)
                if id_match:
                    prop_id = int(id_match.group(1))
                    return {
                        'id_properties': prop_id,
                        'name': f'Property_{prop_id}',
                        'currency': 'Unknown',
                        'backup_response': backup_data['body']
                    }
            
            # Patrón 3: Properties list backup
            if isinstance(backup_data, list):
                # Es una lista de propiedades
                properties = []
                for prop in backup_data:
                    if isinstance(prop, dict) and 'id_properties' in prop:
                        properties.append(prop)
                return properties[0] if properties else None
            
        except Exception as e:
            print(f"Error extrayendo propiedad: {e}")
        
        return None
    
    def comprehensive_property_discovery(self) -> List[Dict]:
        """
        Ejecutar todos los métodos de descubrimiento y consolidar resultados
        """
        print("🚀 INICIO: Descubrimiento Comprehensivo de Propiedades OTASync")
        print("=" * 70)
        
        all_properties = []
        
        # Método 1: Calendar Scan
        try:
            calendar_properties = self.discover_properties_via_calendar_scan()
            all_properties.extend(calendar_properties)
        except Exception as e:
            print(f"❌ Error en Método 1: {e}")
        
        # Método 2: Web Scraping
        try:
            web_properties = self.discover_properties_via_web_scraping()
            all_properties.extend(web_properties)
        except Exception as e:
            print(f"❌ Error en Método 2: {e}")
        
        # Método 3: Backup Analysis
        try:
            backup_properties = self.discover_properties_via_backup_analysis()
            all_properties.extend(backup_properties)
        except Exception as e:
            print(f"❌ Error en Método 3: {e}")
        
        # Consolidar y deduplicar
        consolidated = self._consolidate_properties(all_properties)
        
        print(f"\n📊 RESULTADOS FINALES:")
        print(f"   Total propiedades encontradas: {len(consolidated)}")
        
        for i, prop in enumerate(consolidated):
            print(f"   {i+1}. ID: {prop['id_properties']} - {prop['name']} - Via: {prop['discovered_via']}")
        
        # Guardar resultados
        self._save_discovery_results(consolidated)
        
        return consolidated
    
    def _consolidate_properties(self, properties: List[Dict]) -> List[Dict]:
        """Consolidar y deduplicar propiedades encontradas"""
        seen_ids = set()
        consolidated = []
        
        for prop in properties:
            prop_id = prop.get('id_properties')
            if prop_id and prop_id not in seen_ids:
                seen_ids.add(prop_id)
                consolidated.append(prop)
        
        return consolidated
    
    def _save_discovery_results(self, properties: List[Dict]):
        """Guardar resultados del descubrimiento"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"/home/gordon/Escritorio/scraping/kunas/backups/discovered_properties_{timestamp}.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(properties, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Resultados guardados en: {output_file}")
        except Exception as e:
            print(f"❌ Error guardando resultados: {e}")


if __name__ == "__main__":
    discovery = OTASyncPropertiesDiscovery()
    properties = discovery.comprehensive_property_discovery()
    
    print(f"\n🎉 DESCUBRIMIENTO COMPLETADO")
    print(f"   Propiedades funcionales encontradas: {len(properties)}")
    
    if properties:
        print(f"\n📋 Lista de propiedades para usar en tu cliente:")
        for prop in properties:
            print(f"   - {prop['id_properties']}: {prop['name']}")
    else:
        print(f"\n⚠️  No se encontraron propiedades activas.")
        print(f"   Posibles causas:")
        print(f"   - Permisos de cuenta limitados")
        print(f"   - Cambios en la API")
        print(f"   - Rate limiting temporal")
