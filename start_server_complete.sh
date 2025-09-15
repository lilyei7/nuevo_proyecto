#!/bin/bash
# Script para iniciar el servidor Django correctamente

echo "🚀 Iniciando servidor Django con verificación matemática..."

# Cambiar al directorio del proyecto
cd /home/gordon/Escritorio/scraping/nuevo_proyecto

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo "❌ Error: No se encuentra manage.py"
    echo "Directorio actual: $(pwd)"
    exit 1
fi

# Verificar que el venv existe
if [ ! -f "venv/bin/python" ]; then
    echo "❌ Error: No se encuentra el entorno virtual"
    exit 1
fi

echo "📂 Directorio del proyecto: $(pwd)"
echo "🐍 Python del venv: $(ls -la venv/bin/python)"

# Terminar cualquier proceso Django previo
echo "🧹 Limpiando procesos Django previos..."
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 2

# Verificar que el puerto está libre
if netstat -tuln | grep -q ":8001 "; then
    echo "⚠️ Puerto 8001 ocupado, usando puerto 8003"
    PORT=8003
else
    echo "✅ Puerto 8001 disponible"
    PORT=8001
fi

# Hacer un check del sistema Django
echo "🔍 Verificando sistema Django..."
./venv/bin/python manage.py check

if [ $? -eq 0 ]; then
    echo "✅ Sistema Django verificado correctamente"
    echo "🌐 Iniciando servidor en puerto $PORT..."
    echo ""
    echo "📋 INFORMACIÓN DEL SISTEMA:"
    echo "   🏨 Monitor avanzado: http://127.0.0.1:$PORT/dashboard/monitor/"
    echo "   🧮 Verificación matemática integrada"
    echo "   📊 Dashboard principal: http://127.0.0.1:$PORT/dashboard/"
    echo ""
    echo "✨ Nuevas funcionalidades implementadas:"
    echo "   • Precio base + impuestos por separado"
    echo "   • Margen aplicado sobre subtotal (base + impuestos)"
    echo "   • Verificación automática de cálculos"
    echo "   • Monitor en tiempo real con SSE"
    echo ""
    
    # Iniciar el servidor
    ./venv/bin/python manage.py runserver 127.0.0.1:$PORT
else
    echo "❌ Error en verificación del sistema Django"
    exit 1
fi
