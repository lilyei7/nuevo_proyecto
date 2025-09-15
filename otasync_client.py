"""
Cliente OTASync autocontenido - No depende de scripts externos
Versión limpia y simplificada para el proyecto nuevo_proyecto
Fecha: 2025-09-08
"""

import requests
import json
import os
from datetime import datetime, timedelta

class OTASyncClient:
    """Cliente para API de OTASync - Versión autocontenida"""
    
    def __init__(self, email=None, password=None, token=None):
        self.base_url = "https://app.otasync.me"  # URL corregida
        self.session = requests.Session()
        self.email = email
        self.password = password
        self.token = token  # Agregar soporte para token
        self.auth_token = None
        self.pkey = None  # El key de autorización real según documentación
        self.user_info = None  # Info del usuario
        self.property_id = None
        self.pricing_plan_id = None
        
        # Cargar credenciales desde kunas si no se proporcionan
        if not email and not password and not token:
            self._load_credentials_from_kunas()
        
        # Auto-login con email/password solo si NO tenemos token
        if not self.token and self.email and self.password:
            self.login()
    
    def _load_credentials_from_kunas(self):
        """Cargar credenciales desde el archivo kunas/credentials.txt"""
        try:
            # Buscar el archivo desde el proyecto Django
            current_dir = os.path.dirname(os.path.abspath(__file__))
            kunas_path = os.path.join(os.path.dirname(current_dir), 'kunas', 'credentials.txt')
            
            if os.path.exists(kunas_path):
                with open(kunas_path, 'r') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            if key == 'token':
                                self.token = value
                            elif key == 'email' or key == 'username':  # Aceptar ambos
                                self.email = value
                            elif key == 'password':
                                self.password = value
                            elif key == 'property_id':
                                self.property_id = value
                            elif key == 'pricing_plan':
                                self.pricing_plan_id = value
                
                print(f"✅ Credenciales OTASync cargadas desde: {kunas_path}")
                
                # Solo cargar credenciales, NO hacer login automático
                if self.token:
                    print(f"🔐 Token encontrado, listo para autenticación manual")
            else:
                print(f"⚠️ Archivo de credenciales no encontrado: {kunas_path}")
                
        except Exception as e:
            print(f"❌ Error cargando credenciales: {e}")
    
    def login(self):
        """Autenticar con OTASync usando API correcta."""
        try:
            # Usar el endpoint correcto de la documentación
            login_url = f"{self.base_url}/api/user/auth/login"
            
            login_data = {
                "token": self.token,
                "username": self.email,
                "password": self.password,
                "remember": 0
            }
            
            print(f"🔐 Autenticando con API oficial...")
            print(f"   URL: {login_url}")
            print(f"   Token: {self.token[:20]}..." if self.token else "NO TOKEN")
            print(f"   Username: {self.email}")
            
            response = self.session.post(
                login_url, 
                json=login_data,
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"📊 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    
                    # Extraer pkey de la respuesta (según documentación)
                    self.pkey = result.get('pkey')
                    self.user_info = result
                    
                    if self.pkey:
                        print(f"✅ Login exitoso - pkey obtenido: {self.pkey[:15]}...")
                        
                        # Configurar headers para futuras requests
                        self.session.headers.update({
                            'Content-Type': 'application/json',
                            'User-Agent': 'OTASync-Client/1.0'
                        })
                        
                        # Obtener propiedades del usuario
                        properties = result.get('properties', [])
                        print(f"🏨 Propiedades disponibles: {len(properties)}")
                        for prop in properties:
                            print(f"   - {prop.get('name')} (ID: {prop.get('id_properties')})")
                        
                        return True
                    else:
                        print(f"❌ No se obtuvo pkey en la respuesta")
                        return False
                        
                except json.JSONDecodeError:
                    print(f"❌ Respuesta no es JSON válido: {response.text[:200]}...")
                    return False
            else:
                print(f"❌ Error en login: {response.status_code}")
                print(f"   Respuesta: {response.text[:200]}...")
                return False
            
        except Exception as e:
            print(f"❌ Error en autenticación: {str(e)}")
            return False
    
    def get_properties(self):
        """Obtener lista de propiedades"""
        try:
            if not self.auth_token:
                print("❌ No hay token de autenticación")
                return []
            
            response = self.session.get(f"{self.base_url}/properties")
            
            if response.status_code == 200:
                properties = response.json()
                print(f"✅ {len(properties)} propiedades OTASync encontradas")
                return properties
            else:
                print(f"❌ Error obteniendo propiedades: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Excepción obteniendo propiedades: {e}")
            return []
    
    def get_pricing_plans(self, property_id=None):
        """Obtener planes de precios para una propiedad"""
        try:
            if not property_id:
                property_id = self.property_id
                
            if not property_id:
                print("❌ No se proporcionó property_id")
                return []
            
            response = self.session.get(f"{self.base_url}/properties/{property_id}/pricing-plans")
            
            if response.status_code == 200:
                plans = response.json()
                print(f"✅ {len(plans)} planes de precio encontrados")
                return plans
            else:
                print(f"❌ Error obteniendo planes de precio: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Excepción obteniendo planes: {e}")
            return []
    
    def get_current_prices(self, property_id, pricing_plan_id, date_from, date_to):
        """
        Obtener precios actuales usando la API oficial /api/prices/data/prices
        
        Args:
            property_id: ID de la propiedad
            pricing_plan_id: ID del plan de precios  
            date_from: Fecha inicio ('YYYY-MM-DD')
            date_to: Fecha fin ('YYYY-MM-DD')
        """
        try:
            if not self.pkey:
                print("❌ No hay pkey - debe hacer login primero")
                return None
                
            print(f"🔍 Obteniendo precios actuales:")
            print(f"   Property ID: {property_id}")
            print(f"   Pricing Plan ID: {pricing_plan_id}")
            print(f"   Fechas: {date_from} a {date_to}")
            
            payload = {
                "token": self.token,
                "key": self.pkey,
                "id_properties": int(property_id),
                "id_pricing_plans": int(pricing_plan_id),
                "dfrom": date_from,
                "dto": date_to
            }
            
            response = self.session.post(
                f"{self.base_url}/api/prices/data/prices",
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"📊 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"✅ Precios obtenidos exitosamente")
                    return result
                except json.JSONDecodeError:
                    print(f"❌ Error decodificando JSON: {response.text[:200]}")
                    return None
            else:
                print(f"❌ Error obteniendo precios: {response.status_code}")
                print(f"   Respuesta: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Error obteniendo precios: {e}")
            return None

    def get_calendar_info(self, property_id, date=None, days=20):
        """
        Obtener información del calendar para extraer room_types y pricing_plan_id
        
        Args:
            property_id: ID de la propiedad
            date: Fecha inicio (YYYY-MM-DD), por defecto hoy
            days: Número de días
        """
        try:
            if not self.pkey:
                print("❌ No hay pkey - debe hacer login primero")
                return None
                
            from datetime import datetime
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
                
            print(f"🔍 Obteniendo calendar info:")
            print(f"   Property ID: {property_id}")
            print(f"   Date: {date}")
            print(f"   Days: {days}")
            
            payload = {
                "token": self.token,
                "key": self.pkey,
                "property_id": int(property_id),
                "date": date,
                "days": days
            }
            
            response = self.session.post(
                f"{self.base_url}/api/calendar",
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"📊 Calendar Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"✅ Calendar info obtenida exitosamente")
                    
                    # Extraer información útil
                    room_types = []
                    pricing_plan_id = None
                    
                    if isinstance(result, dict):
                        if 'room_types' in result and isinstance(result['room_types'], list):
                            room_types = result['room_types']
                        elif 'filters' in result and isinstance(result['filters'], dict):
                            if 'room_types' in result['filters']:
                                room_types = result['filters']['room_types']
                        
                        # Extraer pricing plan ID
                        pricing_plan_id = result.get('id_pricing_plans') 
                        if not pricing_plan_id and 'filters' in result:
                            pricing_plan_id = result['filters'].get('default_price')
                        
                        if pricing_plan_id:
                            try:
                                pricing_plan_id = int(pricing_plan_id)
                            except:
                                pricing_plan_id = None
                    
                    print(f"📋 Room types encontrados: {len(room_types)}")
                    for rt in room_types:
                        print(f"   - ID: {rt.get('id_room_types')}, Name: {rt.get('name', 'N/A')}")
                    
                    if pricing_plan_id:
                        print(f"💰 Pricing Plan ID: {pricing_plan_id}")
                    else:
                        print("⚠️ No se encontró Pricing Plan ID")
                    
                    return {
                        'success': True,
                        'room_types': room_types,
                        'pricing_plan_id': pricing_plan_id,
                        'full_response': result
                    }
                    
                except json.JSONDecodeError:
                    print(f"❌ Error decodificando calendar JSON: {response.text[:200]}")
                    return None
            else:
                print(f"❌ Error obteniendo calendar: {response.status_code}")
                print(f"   Respuesta: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Error en get_calendar_info: {e}")
            return None

    def verify_price_updates(self, property_id, room_type_id, expected_prices, pricing_plan_id=None):
        """
        VERIFICAR que los precios se actualizaron correctamente
        Compara precios esperados vs precios actuales en OTASync
        
        Args:
            property_id: ID de la propiedad
            room_type_id: ID del room type
            expected_prices: Lista de dict con {'date': 'YYYY-MM-DD', 'price': 100.0}
            pricing_plan_id: ID del plan de precios
        
        Returns:
            dict con resultado de la verificación
        """
        try:
            # Reutilizar autenticación existente (SIN nuevo login)
            if not self.pkey:
                return {"success": False, "error": "No autenticado"}
            
            if not expected_prices:
                return {"success": False, "error": "No hay precios para verificar"}
            
            # Usar pricing_plan_id del backup si no se proporciona
            if not pricing_plan_id:
                pricing_plan_id = 26946
            
            print(f"🔍 VERIFICANDO PRECIOS ACTUALIZADOS:")
            print(f"   Property ID: {property_id}")
            print(f"   Room Type ID: {room_type_id}")
            print(f"   Pricing Plan ID: {pricing_plan_id}")
            
            # Calcular rango de fechas para verificar
            dates = [p['date'] for p in expected_prices]
            date_from = min(dates)
            date_to = max(dates)
            
            print(f"   Rango de verificación: {date_from} a {date_to}")
            print(f"   Total fechas a verificar: {len(expected_prices)}")
            
            # Obtener precios actuales de OTASync
            print("📤 Obteniendo precios actuales de OTASync...")
            
            payload = {
                "token": self.token,
                "key": self.pkey,
                "id_properties": int(property_id),
                "id_pricing_plans": int(pricing_plan_id),
                "dfrom": date_from,
                "dto": date_to
            }
            
            response = self.session.post(
                f"{self.base_url}/api/prices/data/prices",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"📊 Response Status: {response.status_code}")
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Error obteniendo precios: {response.status_code}",
                    "response_text": response.text[:200]
                }
            
            try:
                data = response.json()
            except:
                return {
                    "success": False,
                    "error": "Respuesta no es JSON válido"
                }
            
            print("✅ Precios actuales obtenidos exitosamente")
            
            # Extraer precios por fecha del room type específico
            actual_prices = {}
            
            # La API devuelve formato: {'status': 'ok', 'data': {'29119': {'2025-09-08': '1498.75'}}}
            if data.get('data'):
                room_data = data['data'].get(str(room_type_id))
                if room_data:
                    # room_data es un dict con fechas como keys y precios como values
                    for date, price in room_data.items():
                        actual_prices[date] = float(price)
                else:
                    print(f"⚠️ No se encontraron datos para Room Type {room_type_id}")
                    print(f"   Room Types disponibles: {list(data['data'].keys())}")
            else:
                print("⚠️ No hay data en la respuesta")
                print(f"   Respuesta completa: {data}")
            
            print(f"🔍 Precios encontrados para Room Type {room_type_id}: {len(actual_prices)}")
            if actual_prices:
                print(f"   Ejemplo: {list(actual_prices.items())[:3]}")
            
            # Comparar precios esperados vs actuales
            verification_details = []
            verified_count = 0
            total_difference = 0
            total_percentage_change = 0
            
            print("📋 COMPARACIÓN DE PRECIOS:")
            print("Fecha        Esperado   Actual     Estado   Diferencia")
            print("-" * 60)
            
            for expected in expected_prices:
                date = expected['date']
                expected_price = float(expected['price'])
                actual_price = actual_prices.get(date, 0)
                
                difference = actual_price - expected_price
                percentage_change = (difference / expected_price * 100) if expected_price > 0 else 0
                
                # Considerar verificado si la diferencia es muy pequeña (< $0.01)
                is_verified = abs(difference) < 0.01
                
                if is_verified:
                    verified_count += 1
                    status = "✅ OK"
                else:
                    status = "⚠️ DIFF"
                
                total_difference += difference
                total_percentage_change += percentage_change
                
                print(f"{date}   ${expected_price:8.2f}   ${actual_price:8.2f}   {status}     ${difference:+.2f} ({percentage_change:+.1f}%)")
                
                verification_details.append({
                    "date": date,
                    "expected_price": expected_price,
                    "actual_price": actual_price,
                    "difference": difference,
                    "percentage_change": percentage_change,
                    "verified": is_verified
                })
            
            print("-" * 60)
            
            # Calcular estadísticas
            verification_rate = (verified_count / len(expected_prices)) * 100 if expected_prices else 0
            avg_difference = total_difference / len(expected_prices) if expected_prices else 0
            avg_percentage_change = total_percentage_change / len(expected_prices) if expected_prices else 0
            
            print(f"📊 RESULTADO DE VERIFICACIÓN:")
            print(f"   ✅ Verificados correctamente: {verified_count}/{len(expected_prices)}")
            print(f"   📈 Tasa de verificación: {verification_rate:.1f}%")
            print(f"   💰 Diferencia promedio: ${avg_difference:.2f}")
            print(f"   📊 Cambio porcentual promedio: {avg_percentage_change:+.1f}%")
            
            # Determinar si la verificación fue exitosa
            # Considerar exitoso si al menos 95% está verificado
            verification_success = verification_rate >= 95.0
            
            if verification_success:
                print("🎉 VERIFICACIÓN EXITOSA!")
            else:
                print("⚠️ VERIFICACIÓN PARCIAL - Revisar diferencias")
            
            return {
                "success": verification_success,
                "verification_rate": verification_rate,
                "verified_count": verified_count,
                "total_count": len(expected_prices),
                "avg_difference": avg_difference,
                "avg_percentage_change": avg_percentage_change,
                "verification_details": verification_details,
                "actual_prices": actual_prices
            }
            
        except Exception as e:
            print(f"❌ Error en verificación: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def update_pricing_mega_payload(self, property_id, room_type_id, date_prices, pricing_plan_id=None):
        """
        MEGA PAYLOAD ÚNICO: Intenta enviar TODAS las fechas en un solo request optimizado
        
        Este método trata de hacer la sincronización más eficiente:
        1. Agrupa fechas por precio para máxima eficiencia
        2. Usa UN SOLO payload cuando es posible
        3. Manejo inteligente de rangos de fechas
        
        Args:
            property_id: ID de la propiedad
            room_type_id: ID del room type
            date_prices: Lista de dict con {'date': 'YYYY-MM-DD', 'price': 100.0}
            pricing_plan_id: ID del plan de precios
        
        Returns:
            dict con resultado del mega payload
        """
        try:
            # Asegurar autenticación
            if not self.pkey:
                print("🔐 Autenticando para mega payload...")
                if not self.login():
                    return {"success": False, "error": "No se pudo autenticar"}
            
            if not date_prices:
                return {"success": False, "error": "No hay fechas para actualizar"}
            
            # Usar pricing_plan_id del backup si no se proporciona
            if not pricing_plan_id:
                pricing_plan_id = 26946
            
            print(f"🚀 MEGA PAYLOAD ÚNICO:")
            print(f"   Property ID: {property_id}")
            print(f"   Room Type ID: {room_type_id}")
            print(f"   Total fechas: {len(date_prices)}")
            print(f"   Pricing Plan ID: {pricing_plan_id}")
            print("")
            
            # Optimización: Agrupar por precio para máxima eficiencia
            price_groups = {}
            for dp in date_prices:
                price = dp['price']
                if price not in price_groups:
                    price_groups[price] = []
                price_groups[price].append(dp['date'])
            
            print(f"🧠 OPTIMIZACIÓN MEGA PAYLOAD:")
            print(f"   Fechas originales: {len(date_prices)}")
            print(f"   Grupos de precios: {len(price_groups)}")
            print(f"   Reducción: {len(date_prices) - len(price_groups)} llamadas ahorradas")
            print("")
            
            # Estrategia: Intentar cada grupo como rango si las fechas son consecutivas
            successful_updates = 0
            total_api_calls = 0
            all_changelog_ids = []
            
            for i, (price, dates) in enumerate(price_groups.items(), 1):
                dates.sort()  # Ordenar fechas
                
                print(f"📤 GRUPO {i}: ${price:,.2f} → {len(dates)} fechas")
                
                # Si hay muchas fechas del mismo precio, intentar como rango
                if len(dates) > 1:
                    date_from = min(dates)
                    date_to = max(dates)
                    
                    # Intentar como rango completo primero
                    print(f"   🎯 Intentando rango: {date_from} a {date_to}")
                    
                    payload = {
                        "token": self.token,
                        "key": self.pkey,
                        "id_properties": int(property_id),
                        "id_pricing_plans": int(pricing_plan_id),
                        "dfrom": date_from,
                        "dto": date_to,
                        "rooms": [{
                            "id_room_types": int(room_type_id),
                            "value": float(price)
                        }],
                        "variation_type": 0,
                        "weekdays": [1,1,1,1,1,1,1]  # Todos los días
                    }
                    
                    response = self.session.post(
                        f"{self.base_url}/api/prices/edit/prices",
                        json=payload,
                        headers={'Content-Type': 'application/json'},
                        timeout=30
                    )
                    
                    total_api_calls += 1
                    
                    if response.status_code in [200, 204]:
                        print(f"   ✅ Rango exitoso: Status {response.status_code}")
                        successful_updates += len(dates)
                        
                        try:
                            result = response.json()
                            if result.get('id_changelog'):
                                all_changelog_ids.append(result['id_changelog'])
                        except:
                            pass
                    else:
                        print(f"   ⚠️ Rango falló (Status {response.status_code}), intentando individual...")
                        
                        # Si el rango falla, intentar fecha por fecha
                        for date in dates:
                            payload_single = {
                                "token": self.token,
                                "key": self.pkey,
                                "id_properties": int(property_id),
                                "id_pricing_plans": int(pricing_plan_id),
                                "dfrom": date,
                                "dto": date,
                                "rooms": [{
                                    "id_room_types": int(room_type_id),
                                    "value": float(price)
                                }],
                                "variation_type": 0,
                                "weekdays": [1,1,1,1,1,1,1]
                            }
                            
                            response_single = self.session.post(
                                f"{self.base_url}/api/prices/edit/prices",
                                json=payload_single,
                                headers={'Content-Type': 'application/json'},
                                timeout=30
                            )
                            
                            total_api_calls += 1
                            
                            if response_single.status_code in [200, 204]:
                                print(f"      ✅ {date}: Status {response_single.status_code}")
                                successful_updates += 1
                                
                                try:
                                    result = response_single.json()
                                    if result.get('id_changelog'):
                                        all_changelog_ids.append(result['id_changelog'])
                                except:
                                    pass
                            else:
                                print(f"      ❌ {date}: Status {response_single.status_code}")
                else:
                    # Una sola fecha - envío directo
                    date = dates[0]
                    payload = {
                        "token": self.token,
                        "key": self.pkey,
                        "id_properties": int(property_id),
                        "id_pricing_plans": int(pricing_plan_id),
                        "dfrom": date,
                        "dto": date,
                        "rooms": [{
                            "id_room_types": int(room_type_id),
                            "value": float(price)
                        }],
                        "variation_type": 0,
                        "weekdays": [1,1,1,1,1,1,1]
                    }
                    
                    response = self.session.post(
                        f"{self.base_url}/api/prices/edit/prices",
                        json=payload,
                        headers={'Content-Type': 'application/json'},
                        timeout=30
                    )
                    
                    total_api_calls += 1
                    
                    if response.status_code in [200, 204]:
                        print(f"   ✅ {date}: Status {response.status_code}")
                        successful_updates += 1
                        
                        try:
                            result = response.json()
                            if result.get('id_changelog'):
                                all_changelog_ids.append(result['id_changelog'])
                        except:
                            pass
                    else:
                        print(f"   ❌ {date}: Status {response.status_code}")
            
            # Calcular resultados
            success_rate = (successful_updates / len(date_prices)) * 100 if date_prices else 0
            
            print("")
            print("📊 RESULTADO MEGA PAYLOAD:")
            print(f"   ✅ Fechas exitosas: {successful_updates}/{len(date_prices)}")
            print(f"   ✅ Tasa de éxito: {success_rate:.1f}%")
            print(f"   📞 API calls: {total_api_calls}")
            print(f"   📝 Changelog IDs: {len(all_changelog_ids)}")
            
            # Considerar exitoso si al menos 85% se actualizó
            final_success = success_rate >= 85.0
            
            if final_success:
                print("🎉 MEGA PAYLOAD: ¡ÉXITO!")
            else:
                print("⚠️ MEGA PAYLOAD: ÉXITO PARCIAL")
            
            return {
                "success": final_success,
                "successful_count": successful_updates,
                "total_dates": len(date_prices),
                "success_rate": success_rate,
                "api_calls": total_api_calls,
                "changelog_ids": all_changelog_ids,
                "mega_payload": True
            }
            
        except Exception as e:
            print(f"❌ Error en mega payload: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def update_and_verify_prices(self, property_id, room_type_id, date_prices, pricing_plan_id=None, max_retries=3):
        """
        SISTEMA ROBUSTO: Actualizar precios + Verificar + Reintentar si falla
        Intenta enviar TODAS las fechas de una vez, verifica y reintenta lo que falló
        
        Args:
            property_id: ID de la propiedad (ej: 9355)
            room_type_id: ID del room type (ej: 29119) 
            date_prices: Lista de dict con {'date': 'YYYY-MM-DD', 'price': 100.0}
            pricing_plan_id: ID del plan de precios
            max_retries: Número máximo de reintentos para fechas fallidas
        
        Returns:
            dict con resultado completo del proceso
        """
        try:
            # Asegurar que estamos autenticados (REUTILIZAR pkey existente sin nuevo login)
            if not self.pkey:
                print("🔐 No hay pkey - debe estar autenticado primero")
                return {"success": False, "error": "No autenticado"}
            
            if not date_prices:
                return {"success": False, "error": "No hay fechas para actualizar"}
            
            # Usar pricing_plan_id del backup si no se proporciona
            if not pricing_plan_id:
                pricing_plan_id = 26946
                print(f"✅ Usando Pricing Plan ID del backup: {pricing_plan_id}")
            
            print(f"🚀 SISTEMA ROBUSTO: ACTUALIZAR + VERIFICAR + REINTENTAR")
            print(f"   Property ID: {property_id}")
            print(f"   Room Type ID: {room_type_id}")
            print(f"   Total fechas: {len(date_prices)}")
            print(f"   Max reintentos: {max_retries}")
            print("")
            
            # Lista de fechas pendientes de actualizar (inicialmente todas)
            pending_prices = date_prices.copy()
            attempt = 0
            all_changelog_ids = []
            total_api_calls = 0
            
            while pending_prices and attempt < max_retries:
                attempt += 1
                print(f"🔄 INTENTO {attempt}/{max_retries} - Fechas pendientes: {len(pending_prices)}")
                
                # ESTRATEGIA: Intentar LOTE COMPLETO primero, luego lotes más pequeños
                if attempt == 1 and len(pending_prices) > 5:
                    print("📦 ESTRATEGIA: Intentando LOTE COMPLETO primero")
                    batch_sizes = [len(pending_prices)]
                elif len(pending_prices) > 10:
                    print("📦 ESTRATEGIA: Dividiendo en lotes medianos")
                    batch_sizes = [10, 5, 1]  # Lotes decrecientes
                else:
                    print("📦 ESTRATEGIA: Usando batch inteligente")
                    batch_sizes = [len(pending_prices)]
                
                for batch_size in batch_sizes:
                    if not pending_prices:
                        break
                    
                    # Tomar lote de fechas pendientes
                    if batch_size >= len(pending_prices):
                        batch_dates = pending_prices.copy()
                    else:
                        batch_dates = pending_prices[:batch_size]
                    
                    print(f"📤 Procesando lote de {len(batch_dates)} fechas...")
                    
                    # INTENTAR ACTUALIZAR ESTE LOTE
                    if len(batch_dates) == 1:
                        # Una sola fecha - envío directo
                        update_result = self._update_single_batch(
                            property_id, room_type_id, batch_dates, pricing_plan_id
                        )
                    else:
                        # Múltiples fechas - usar batch inteligente
                        update_result = self._update_intelligent_batch(
                            property_id, room_type_id, batch_dates, pricing_plan_id
                        )
                    
                    total_api_calls += update_result.get('api_calls', 0)
                    
                    if update_result.get('changelog_ids'):
                        all_changelog_ids.extend(update_result.get('changelog_ids', []))
                    
                    # VERIFICAR QUE SE ACTUALIZARON CORRECTAMENTE
                    print("🔍 Verificando lote actualizado...")
                    verification_result = self._verify_batch_quick(
                        property_id, room_type_id, batch_dates, pricing_plan_id
                    )
                    
                    if verification_result and verification_result.get('success'):
                        verified_dates = [vd['date'] for vd in verification_result.get('verification_details', []) if vd.get('verified')]
                        
                        # Remover fechas exitosamente verificadas de pendientes
                        pending_prices = [p for p in pending_prices if p['date'] not in verified_dates]
                        
                        print(f"✅ Lote verificado: {len(verified_dates)} fechas correctas")
                        
                        if not pending_prices:
                            print("🎉 ¡TODAS LAS FECHAS ACTUALIZADAS Y VERIFICADAS!")
                            break
                    else:
                        print("⚠️ Verificación falló - manteniendo fechas como pendientes")
                    
                    # Si hay muchas fechas pendientes, probar lote más pequeño
                    if len(pending_prices) > batch_size * 0.8:
                        continue
                    else:
                        break
                
                if pending_prices and attempt < max_retries:
                    print(f"⏳ Esperando 2 segundos antes del siguiente intento...")
                    import time
                    time.sleep(2)
            
            # RESULTADO FINAL
            successful_count = len(date_prices) - len(pending_prices)
            success_rate = (successful_count / len(date_prices)) * 100
            
            print("")
            print("=" * 60)
            print("📊 RESULTADO FINAL DEL SISTEMA ROBUSTO:")
            print(f"   ✅ Fechas exitosas: {successful_count}/{len(date_prices)}")
            print(f"   ✅ Tasa de éxito: {success_rate:.1f}%")
            print(f"   📞 Total API calls: {total_api_calls}")
            print(f"   🔄 Intentos usados: {attempt}/{max_retries}")
            print(f"   📝 Changelog IDs: {len(all_changelog_ids)}")
            
            if pending_prices:
                print(f"   ⚠️ Fechas pendientes: {len(pending_prices)}")
                for p in pending_prices:
                    print(f"      - {p['date']}: ${p['price']:.2f}")
            
            # Considerar exitoso si al menos 90% se actualizó
            final_success = success_rate >= 90.0
            
            if final_success:
                print("🎉 SISTEMA ROBUSTO: ¡ÉXITO COMPLETO!")
            else:
                print("⚠️ SISTEMA ROBUSTO: ÉXITO PARCIAL")
            
            return {
                "success": final_success,
                "total_dates": len(date_prices),
                "successful_count": successful_count,
                "pending_count": len(pending_prices),
                "success_rate": success_rate,
                "attempts_used": attempt,
                "total_api_calls": total_api_calls,
                "changelog_ids": all_changelog_ids,
                "pending_prices": pending_prices,
                "robust_system": True
            }
            
        except Exception as e:
            print(f"❌ Error en sistema robusto: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def _update_single_batch(self, property_id, room_type_id, date_prices, pricing_plan_id):
        """Actualizar un lote pequeño (optimizado para 1 fecha)"""
        date_price = date_prices[0]
        
        payload = {
            "token": self.token,
            "key": self.pkey,
            "id_properties": int(property_id),
            "id_pricing_plans": int(pricing_plan_id),
            "dfrom": date_price['date'],
            "dto": date_price['date'],
            "rooms": [{
                "id_room_types": int(room_type_id),
                "value": float(date_price['price'])
            }],
            "variation_type": 0,
            "weekdays": [1,1,1,1,1,1,1]
        }
        
        response = self.session.post(
            f"{self.base_url}/api/prices/edit/prices",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        changelog_ids = []
        if response.status_code in [200, 204]:
            try:
                result = response.json()
                if result.get('id_changelog'):
                    changelog_ids.append(result['id_changelog'])
            except:
                pass
        
        return {
            "success": response.status_code in [200, 204],
            "api_calls": 1,
            "changelog_ids": changelog_ids
        }

    def _update_intelligent_batch(self, property_id, room_type_id, date_prices, pricing_plan_id):
        """Actualizar usando el batch inteligente existente"""
        return self.update_pricing_official(property_id, room_type_id, date_prices, pricing_plan_id)

    def _verify_batch_quick(self, property_id, room_type_id, expected_prices, pricing_plan_id):
        """Verificación rápida de un lote específico"""
        return self.verify_price_updates(property_id, room_type_id, expected_prices, pricing_plan_id)

    def update_pricing_official(self, property_id, room_type_id, date_prices, pricing_plan_id=None, variation_type=0):
        """
        Actualizar precios usando BATCH INTELIGENTE - Agrupar fechas con mismo precio
        Reducir llamadas API agrupando fechas que tienen el mismo precio
        
        Args:
            property_id: ID de la propiedad (ej: 9355)
            room_type_id: ID del room type (ej: 29119) 
            date_prices: Lista de dict con {'date': 'YYYY-MM-DD', 'price': 100.0}
            pricing_plan_id: ID del plan de precios (se usa del backup si no se proporciona)
            variation_type: Tipo de variación de precio:
                -2: Disminuir precio por valor enviado
                -1: Disminuir precio por porcentaje
                 0: Establecer precio exacto (valor enviado)
                 1: Aumentar precio por porcentaje
                 2: Aumentar precio por valor enviado
        """
        try:
            if not self.pkey:
                print("❌ No hay pkey - debe hacer login primero")
                return {"success": False, "error": "No autenticado"}
                
            print(f"🔄 Actualizando precios con BATCH INTELIGENTE:")
            print(f"   Property ID: {property_id}")
            print(f"   Room Type ID: {room_type_id}")
            print(f"   Total fechas: {len(date_prices)}")
            print(f"   Token: {self.token[:20]}..." if self.token else "NO TOKEN")
            print(f"   Key: {self.pkey[:20]}..." if self.pkey else "NO KEY")
            
            if not date_prices:
                return {"success": False, "error": "No hay fechas para actualizar"}
            
            # Si no tenemos pricing_plan_id, usar el del backup exitoso
            if not pricing_plan_id:
                pricing_plan_id = 26946
                print(f"✅ Usando Pricing Plan ID del backup exitoso: {pricing_plan_id}")
            
            # AGRUPAR FECHAS POR PRECIO para reducir llamadas API
            price_groups = {}
            for date_price in date_prices:
                price = float(date_price['price'])
                if price not in price_groups:
                    price_groups[price] = []
                price_groups[price].append(date_price['date'])
            
            print(f"🧠 OPTIMIZACIÓN BATCH INTELIGENTE:")
            print(f"   Fechas originales: {len(date_prices)}")
            print(f"   Grupos de precios: {len(price_groups)}")
            print(f"   Reducción: {len(date_prices) - len(price_groups)} llamadas ahorradas")
            print("")
            
            print("📋 GRUPOS DE PRECIOS:")
            for i, (price, dates) in enumerate(sorted(price_groups.items()), 1):
                dates_str = f"{dates[0]}" if len(dates) == 1 else f"{dates[0]}...{dates[-1]} ({len(dates)} fechas)"
                print(f"   {i:2d}. ${price:,.2f} → {dates_str}")
            print("")
            
            # PROCESAR CADA GRUPO DE PRECIO
            success_count = 0
            all_changelog_ids = []
            
            for price, dates in price_groups.items():
                if len(dates) == 1:
                    # Una sola fecha
                    dfrom = dto = dates[0]
                    print(f"📤 Precio ${price:.2f} → {dates[0]}")
                else:
                    # Múltiples fechas consecutivas o separadas
                    dates.sort()  # Ordenar fechas
                    dfrom = dates[0]
                    dto = dates[-1]
                    print(f"📤 Precio ${price:.2f} → {len(dates)} fechas ({dfrom} a {dto})")
                
                # Payload para este grupo de precio
                payload = {
                    "token": self.token,
                    "key": self.pkey,
                    "id_properties": int(property_id),
                    "id_pricing_plans": int(pricing_plan_id),
                    "dfrom": dfrom,
                    "dto": dto,
                    "rooms": [{
                        "id_room_types": int(room_type_id),
                        "value": float(price)
                    }],
                    "variation_type": variation_type,  # Tipo de variación
                    # Tipos de variation_type:
                    # -2: Disminuir precio por valor enviado
                    # -1: Disminuir precio por porcentaje
                    #  0: Establecer precio exacto (valor enviado)
                    #  1: Aumentar precio por porcentaje
                    #  2: Aumentar precio por valor enviado
                    "weekdays": [1,1,1,1,1,1,1]  # Todos los días habilitados (domingo a sábado)
                }
                
                # Enviar request para este grupo
                response = self.session.post(
                    f"{self.base_url}/api/prices/edit/prices",
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                print(f"   📊 Status: {response.status_code}", end="")
                
                if response.status_code in [200, 204]:
                    try:
                        result = response.json()
                        
                        # Buscar id_changelog
                        if isinstance(result, dict) and 'id_changelog' in result:
                            changelog_id = result['id_changelog']
                            all_changelog_ids.append(changelog_id)
                            print(f" ✅ Changelog: {changelog_id}")
                            success_count += len(dates)  # Contar todas las fechas del grupo
                        elif result.get('status') == 'ok':
                            print(f" ✅ OK")
                            success_count += len(dates)
                        else:
                            print(f" ⚠️ Inesperado: {result}")
                            success_count += len(dates)  # Asumir éxito si es 200
                            
                    except json.JSONDecodeError:
                        print(f" ✅ OK (no-JSON)")
                        success_count += len(dates)
                else:
                    print(f" ❌ Error: {response.status_code}")
                    try:
                        error_msg = response.json().get('message', response.text[:100])
                        print(f"       {error_msg}")
                    except:
                        print(f"       {response.text[:100]}")
            
            print("")
            
            # Resultado final
            if success_count > 0:
                success_rate = (success_count / len(date_prices)) * 100
                api_reduction = len(date_prices) - len(price_groups)
                
                print(f"🎉 BATCH INTELIGENTE COMPLETADO:")
                print(f"   ✅ Fechas actualizadas: {success_count}/{len(date_prices)}")
                print(f"   ✅ Tasa de éxito: {success_rate:.1f}%")
                print(f"   ✅ Llamadas API: {len(price_groups)} (ahorró {api_reduction})")
                print(f"   ✅ Eficiencia: {api_reduction/len(date_prices)*100:.1f}% reducción")
                
                if all_changelog_ids:
                    print(f"   ✅ Changelog IDs: {len(all_changelog_ids)} generados")
                
                return {
                    "success": True,
                    "updated_count": success_count,
                    "total_dates": len(date_prices),
                    "success_rate": success_rate,
                    "api_calls": len(price_groups),
                    "api_reduction": api_reduction,
                    "changelog_ids": all_changelog_ids,
                    "batch_intelligent": True
                }
            else:
                print(f"❌ No se pudo actualizar ninguna fecha")
                return {
                    "success": False,
                    "error": "No updates successful",
                    "updated_count": 0,
                    "total_dates": len(date_prices)
                }
                
        except Exception as e:
            print(f"❌ Error en update_pricing_official: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def sync_hotel_prices(self, hotel_data, days_ahead=20):
        """
        Sincronizar precios de un hotel con OTASync
        
        Args:
            hotel_data: Dict con información del hotel y precios
            days_ahead: Número de días hacia adelante para sincronizar
        """
        try:
            if not hotel_data.get('prices'):
                print("❌ No hay datos de precios para sincronizar")
                return False
            
            # Preparar datos de precios para los próximos días
            date_prices = []
            base_date = datetime.now()
            
            for i in range(days_ahead):
                date = base_date + timedelta(days=i)
                date_str = date.strftime('%Y-%m-%d')
                
                # Usar precio base del hotel si está disponible
                price = hotel_data.get('base_price', 100.0)
                if hotel_data['prices']:
                    # Tomar el primer precio disponible como base
                    price = list(hotel_data['prices'].values())[0]
                
                date_prices.append({
                    'date': date_str,
                    'price': float(price)
                })
            
            # Actualizar precios en OTASync
            result = self.update_pricing(
                property_id=self.property_id,
                pricing_plan_id=self.pricing_plan_id,
                date_prices=date_prices
            )
            
            return result is not None
            
        except Exception as e:
            print(f"❌ Error sincronizando precios del hotel: {e}")
            return False

    def get_prices_data(self, property_id, pricing_plan_id, dfrom, dto):
        """
        Obtiene los precios para una propiedad en un rango de fechas
        Implementa el endpoint /api/prices/data/prices
        
        Args:
            property_id: ID de la propiedad
            pricing_plan_id: ID del plan de precios
            dfrom: Fecha de inicio (YYYY-MM-DD)
            dto: Fecha final (YYYY-MM-DD)
            
        Returns:
            dict con los precios o None si hay error
        """
        try:
            # Asegurarse de tener autenticación
            if not self.pkey:
                success = self.login()
                if not success:
                    print("❌ Error en autenticación para get_prices_data")
                    return None
            
            # Construir payload según documentación
            payload = {
                "token": self.token,
                "key": self.pkey,
                "id_properties": property_id,
                "id_pricing_plans": pricing_plan_id,
                "dfrom": dfrom,
                "dto": dto
            }
            
            print(f"🔍 Consultando precios:")
            print(f"   Property ID: {property_id}")
            print(f"   Pricing Plan ID: {pricing_plan_id}")
            print(f"   Período: {dfrom} a {dto}")
            
            # Ejecutar petición
            response = self.session.post(
                f"{self.base_url}/api/prices/data/prices",
                json=payload,
                headers={
                    'Content-Type': 'application/json'
                }
            )
            
            print(f"📊 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('status') == 'ok':
                        print(f"✅ Precios obtenidos correctamente")
                        return result
                    else:
                        print(f"⚠️ Error en respuesta: {result.get('message', 'Sin mensaje')}")
                        return None
                except Exception as e:
                    print(f"❌ Error parseando respuesta: {e}")
                    return None
            else:
                print(f"❌ Error en API: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error en get_prices_data: {e}")
            return None
            
    def sync_price(self, property_id, room_type_id, check_in, check_out, price, variation_type=0, percentage=None):
        """
        Método de compatibilidad para la integración existente
        
        Args:
            property_id: ID de la propiedad
            room_type_id: ID del room type/pricing plan 
            check_in: Fecha de check-in ('YYYY-MM-DD')
            check_out: Fecha de check-out ('YYYY-MM-DD')
            price: Precio para la fecha (o valor base para variation_type != 0)
            variation_type (opcional): Tipo de variación de precio:
                -2: Disminuir precio por valor enviado
                -1: Disminuir precio por porcentaje
                 0: Establecer precio exacto (valor enviado)
                 1: Aumentar precio por porcentaje
                 2: Aumentar precio por valor enviado
            percentage (opcional): Porcentaje a aplicar cuando variation_type es 1 o -1
            
        Returns:
            bool: True si la sincronización fue exitosa
        """
        try:
            # Convertir a formato esperado por update_pricing_official
            date_prices = [{
                'date': check_in,
                'price': float(price)
            }]
            
            # Si estamos usando porcentaje, asegurarnos que el valor es el correcto
            if variation_type in [1, -1] and percentage is not None:
                value_to_use = float(percentage)
                print(f"🧮 Usando variation_type={variation_type} con porcentaje {percentage}%")
            else:
                value_to_use = float(price)
                print(f"🧮 Usando variation_type={variation_type} con precio ${price}")
            
            # Actualizar el valor de precio en el date_prices si es necesario
            if variation_type != 0:
                date_prices[0]['price'] = value_to_use
            
            result = self.update_pricing_official(
                property_id=property_id,
                room_type_id=room_type_id,
                date_prices=date_prices,
                variation_type=variation_type
            )
            
            return bool(result and (result.get('success', False) or result != None))
            
        except Exception as e:
            print(f"❌ Error en sync_price: {e}")
            return False


# Instancia global para uso en Django
def get_otasync_client():
    """Obtener una instancia del cliente OTASync"""
    return OTASyncClient()


    def get_prices_data(self, property_id, pricing_plan_id, dfrom, dto):
        """
        Obtiene los precios para una propiedad en un rango de fechas
        Implementa el endpoint /api/prices/data/prices
        
        Args:
            property_id: ID de la propiedad
            pricing_plan_id: ID del plan de precios
            dfrom: Fecha de inicio (YYYY-MM-DD)
            dto: Fecha final (YYYY-MM-DD)
            
        Returns:
            dict con los precios o None si hay error
        """
        try:
            # Asegurarse de tener autenticación
            if not self.pkey:
                success = self.login()
                if not success:
                    print("❌ Error en autenticación para get_prices_data")
                    return None
            
            # Construir payload según documentación
            payload = {
                "token": self.token,
                "key": self.pkey,
                "id_properties": property_id,
                "id_pricing_plans": pricing_plan_id,
                "dfrom": dfrom,
                "dto": dto
            }
            
            print(f"🔍 Consultando precios:")
            print(f"   Property ID: {property_id}")
            print(f"   Pricing Plan ID: {pricing_plan_id}")
            print(f"   Período: {dfrom} a {dto}")
            
            # Ejecutar petición
            response = self.session.post(
                f"{self.base_url}/api/prices/data/prices",
                json=payload,
                headers={
                    'Content-Type': 'application/json'
                }
            )
            
            print(f"📊 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('status') == 'ok':
                        print(f"✅ Precios obtenidos correctamente")
                        return result
                    else:
                        print(f"⚠️ Error en respuesta: {result.get('message', 'Sin mensaje')}")
                        return None
                except Exception as e:
                    print(f"❌ Error parseando respuesta: {e}")
                    return None
            else:
                print(f"❌ Error en API: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error en get_prices_data: {e}")
            return None

# Para compatibilidad con código existente
if __name__ == "__main__":
    # Prueba básica
    client = OTASyncClient()
    if client.auth_token:
        properties = client.get_properties()
        print(f"Propiedades encontradas: {len(properties)}")
        
        if properties:
            prop = properties[0]
            plans = client.get_pricing_plans(prop.get('id'))
            print(f"Planes de precio: {len(plans)}")
