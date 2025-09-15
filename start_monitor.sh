#!/bin/bash
# 🚀 SCRIPT DE INICIO RÁPIDO PARA MONITOR DE SCRAPING
# ================================================

echo "🏨 Iniciando Monitor de Scraping Hotel"
echo "=================================="

# Navegar al directorio del proyecto
cd /home/runner/work/nuevo_proyecto/nuevo_proyecto

# Verificar que Django esté instalado
echo "📦 Verificando dependencias..."
python -c "import django; print(f'✅ Django {django.get_version()}')" || {
    echo "❌ Error: Django no está instalado"
    echo "💡 Instalando dependencias..."
    pip install -r requirements.txt
    pip install django crispy-bootstrap5 Pillow whitenoise
}

# Aplicar migraciones
echo "🔄 Aplicando migraciones..."
python manage.py migrate --noinput

# Crear superusuario si no existe
echo "👤 Verificando usuario administrador..."
python -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✅ Usuario admin creado (admin/admin123)')
else:
    print('ℹ️ Usuario admin ya existe')
"

# Crear hoteles de ejemplo si no existen
echo "🏨 Creando hoteles de ejemplo..."
python -c "
from hotels.models import Hotel
sample_hotels = [
    {'name': 'Hotel Grand Plaza', 'url': 'https://example.com/hotel1', 'status': 'active'},
    {'name': 'Resort Paradise Beach', 'url': 'https://example.com/hotel2', 'status': 'active'},
    {'name': 'City Center Inn', 'url': 'https://example.com/hotel3', 'status': 'active'},
    {'name': 'Mountain View Lodge', 'url': 'https://example.com/hotel4', 'status': 'active'},
    {'name': 'Oceanfront Suites', 'url': 'https://example.com/hotel5', 'status': 'active'},
]

created_count = 0
for hotel_data in sample_hotels:
    hotel, created = Hotel.objects.get_or_create(
        name=hotel_data['name'],
        defaults={
            'url': hotel_data['url'],
            'status': hotel_data['status'],
            'description': f'Hotel de prueba: {hotel_data[\"name\"]}'
        }
    )
    if created:
        created_count += 1

print(f'✅ {created_count} hoteles creados, {Hotel.objects.count()} total')
"

echo ""
echo "🎉 ¡Monitor listo!"
echo "==================="
echo "🌐 URL del Monitor: http://82.27.100.163:8000/dashboard/monitor/integrated/"
echo "👤 Login Admin: admin / admin123"
echo "📊 Dashboard: http://82.27.100.163:8000/dashboard/"
echo ""
echo "🚀 Iniciando servidor Django..."
echo "   Presiona Ctrl+C para detener"
echo ""

# Iniciar servidor Django
python manage.py runserver 0.0.0.0:8000