#!/bin/bash

# Script de Limpieza del Proyecto
# ===============================

echo "🧹 Iniciando limpieza del proyecto..."

cd /home/gordon/Escritorio/scraping/nuevo_proyecto

# Eliminar archivos de prueba
echo "❌ Eliminando archivos de prueba..."
find . -name "test_*.py" -delete
find . -name "*_test.py" -delete
find . -name "tests.py" -delete

# Eliminar archivos temporales
echo "❌ Eliminando archivos temporales..."
find . -name "*.tmp" -delete
find . -name "*.temp" -delete
find . -name "*~" -delete

# Eliminar cache de Python
echo "❌ Eliminando cache de Python..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete

# Eliminar logs antiguos
echo "❌ Eliminando logs antiguos..."
find . -name "*.log" -delete
find . -name "*.log.*" -delete

# Eliminar archivos de backup
echo "❌ Eliminando backups..."
find . -name "*.bak" -delete
find . -name "*.backup" -delete

# Eliminar archivos de debug
echo "❌ Eliminando archivos de debug..."
find . -name "debug_*.py" -delete
find . -name "*_debug.py" -delete
find . -name "debug_*.js" -delete
find . -name "*debug*.html" -delete

echo "✅ Limpieza completada!"
echo "📊 Archivos restantes: $(find . -type f | wc -l)"
