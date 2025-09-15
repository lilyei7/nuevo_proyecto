# 🏨 Nuevo Proyecto - Hotel Scraper

Proyecto limpio y optimizado para scraping hotelero con integración OTASync.

## 📁 Estructura del Proyecto

### Archivos Principales
- `app.py` - Aplicación Flask principal
- `intelligent_scraper.py` - Sistema de scraping inteligente
- `otasync_integration.py` - Integración con OTASync API
- `otasync_client.py` - Cliente OTASync principal
- `manage.py` - Scripts de gestión
- `requirements.txt` - Dependencias del proyecto
- `.env` - Configuración de variables de entorno
- `schema.sql` - Estructura de base de datos

### Módulos Especializados
- `otasync_api_client.py` - Cliente API avanzado
- `otasync_price_manager.py` - Gestor de precios
- `otasync_properties_discovery.py` - Descubrimiento de propiedades
- `otasync_scraper_integration.py` - Integración scraper-OTASync
- `hotel_management_service.py` - Servicio de gestión hotelera
- `socket_manager.py` - Gestión de WebSockets
- `setup_hotel.py` - Configuración inicial de hoteles

### Directorios
- `scraper/` - Módulos del sistema de scraping
- `kunas/` - Integración con sistema Kunas
- `hotels/` - Gestión de datos hoteleros  
- `authentication/` - Sistema de autenticación
- `dashboard/` - Panel de control
- `static/` - Archivos estáticos (CSS, JS, imágenes)
- `staticfiles/` - Archivos estáticos compilados
- `templates/` - Plantillas HTML

### Integraciones
- `lodgify_integration.py` - Integración con Lodgify

## 🚀 Uso

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
python app.py
```

## ✅ Limpieza Realizada

Se eliminaron los siguientes tipos de archivos:
- ❌ Archivos de prueba (`test_*.py`, `*_test.py`)
- ❌ Documentación redundante (`*.md` duplicados)
- ❌ Archivos de debug y demo (`debug_*.py`, `demo_*.py`)
- ❌ Scripts temporales y de monitoreo
- ❌ Archivos duplicados de OTASync
- ❌ Cache de Python (`__pycache__`, `*.pyc`)
- ❌ Archivos estáticos de Django admin
- ❌ Templates de prueba y debug
- ❌ Archivos vacíos de calendario Kunas
- ❌ Archivos JavaScript de testing
- ❌ Templates de monitoreo

## 📋 Estado Actual

El proyecto está limpio y contiene **133 archivos** con solo lo esencial para:
- ✅ Sistema de scraping inteligente
- ✅ Integración completa con OTASync
- ✅ Gestión hotelera
- ✅ Sistema de calendarios Kunas
- ✅ Panel de control y autenticación
- ✅ APIs y servicios web
