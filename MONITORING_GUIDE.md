# 📡 Monitor de Scraping en Tiempo Real

## ✨ Características Principales

Este sistema de monitoreo integrado permite ver el progreso del scraping y logs en tiempo real **sin necesidad de servidores adicionales**.

### 🎯 Funcionalidades

- **Monitor en Tiempo Real**: Logs streaming con actualización automática cada 3 segundos
- **Control de Scraping**: Botones para iniciar/detener scraping desde la interfaz web
- **Filtros Avanzados**: Por nivel de log (Debug, Info, Warning, Error)
- **Estadísticas Live**: Total de logs, errores, tasa de éxito, última actualización
- **Exportación**: Descarga logs en formato JSON
- **Auto-scroll**: Seguimiento automático de nuevos logs
- **Sin Dependencias Externas**: Funciona completamente con Django cache

## 🚀 Acceso Rápido

### URLs Principales:
- **Monitor Principal**: http://82.27.100.163:8000/dashboard/monitor/integrated/
- **Dashboard**: http://82.27.100.163:8000/dashboard/
- **Admin Panel**: http://82.27.100.163:8000/admin/

### Credenciales por Defecto:
- **Usuario**: admin
- **Contraseña**: admin123

## 📋 Cómo Usar

### 1. Iniciar el Sistema
```bash
# Ejecutar script de inicio automático
./start_monitor.sh

# O manualmente:
python manage.py runserver 0.0.0.0:8000
```

### 2. Acceder al Monitor
1. Abrir navegador web
2. Ir a: `http://82.27.100.163:8000/dashboard/monitor/integrated/`
3. Hacer clic en "▶️ Iniciar Monitor"

### 3. Iniciar Scraping
1. Hacer clic en "🚀 Iniciar Scraping"
2. Confirmar en el diálogo
3. Observar logs en tiempo real

### 4. Controles Disponibles

| Botón | Función |
|-------|---------|
| ▶️ Iniciar Monitor | Activa streaming de logs |
| ⏹️ Detener | Para el streaming |
| 🚀 Iniciar Scraping | Inicia proceso de scraping |
| 🛑 Detener Scraping | Cancela scraping en progreso |
| 🗑️ Limpiar | Limpia logs del buffer |
| 📥 Exportar | Descarga logs en JSON |

## 🎨 Interpretación de Logs

### Colores y Símbolos:
- 🔍 **Azul**: Proceso de scraping iniciado
- ✅ **Verde**: Scraping exitoso con precio obtenido
- ❌ **Rojo**: Error en scraping
- ⚠️ **Naranja**: Advertencias del sistema
- 📋 **Gris**: Información general
- 🎯 **Azul**: Progreso de procesamiento

### Ejemplo de Log:
```
[5:25:31 PM] [scraper] 🔍 Scrapeando Hotel Grand Plaza (1/5)
[5:25:33 PM] [scraper] ✅ Hotel Grand Plaza: $1,250.50 MXN obtenido
```

## ⚙️ Configuración Avanzada

### Variables de Entorno (.env):
```bash
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
```

### Configuración de Cache (settings.py):
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 600,  # 10 minutos
    }
}
```

## 🛠️ API Endpoints

### Logs en Tiempo Real:
```
GET /dashboard/api/logs/?limit=50&level=INFO&since=2023-09-15T10:00:00
```

### Control de Scraping:
```
POST /dashboard/api/start-scraping/
POST /dashboard/api/stop-scraping/
```

### Limpiar Logs:
```
POST /dashboard/api/logs/clear/
```

## 🔧 Troubleshooting

### Problema: No aparecen logs
**Solución**: Verificar que Django cache esté funcionando:
```python
from django.core.cache import cache
cache.set('test', 'working', 30)
print(cache.get('test'))  # Debe mostrar 'working'
```

### Problema: Scraping no inicia
**Solución**: Verificar logs del servidor Django y permisos de base de datos.

### Problema: 500 Error
**Solución**: Verificar migraciones aplicadas:
```bash
python manage.py migrate
```

## 📊 Estadísticas Disponibles

El monitor muestra en tiempo real:
- **Total Logs**: Cantidad de logs generados
- **Errores**: Logs con nivel ERROR
- **Tasa Éxito**: Porcentaje de operaciones exitosas
- **Última Act.**: Timestamp de última actualización
- **Estado Conexión**: 🟢 Activo / 🔴 Inactivo

## 🎯 Casos de Uso

1. **Monitoreo de Scraping Masivo**: Ver progreso de múltiples hoteles
2. **Debugging de Errores**: Filtrar solo logs ERROR para diagnosis
3. **Análisis de Performance**: Exportar logs para análisis posterior
4. **Control Operativo**: Iniciar/detener scraping según necesidad

## 📝 Notas Técnicas

- **Sin WebSockets**: Usa polling AJAX inteligente
- **Cache Local**: Almacena logs en memoria Django
- **Threading**: Scraping ejecuta en hilos separados
- **Responsive**: Compatible con móviles y tablets
- **Auto-cleanup**: Limita logs a 500 entradas máximo

## 🎉 ¡Sistema Listo!

El monitor está completamente funcional y listo para usar. No requiere configuración adicional de servidores externos.

**¡Happy Scraping!** 🚀