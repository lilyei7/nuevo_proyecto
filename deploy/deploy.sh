#!/usr/bin/env bash
set -euo pipefail

# Script de despliegue simple que copia el tar del proyecto al servidor y lo extrae.
# NO almacenes contraseñas en este script. Usa clave SSH (recomendada) o deja que ssh/rsync pidan la contraseña.
# Uso: ./deploy.sh [user@host] [remote_path]

HOST=${1:-root@168.231.112.40}
REMOTE_PATH=${2:-/opt/hotel_scraper}
TARFILE="../nuevo_proyecto.tar.gz"

if [ ! -f "$TARFILE" ]; then
  echo "Tar file $TARFILE not found. Run this from inside the proyecto directory or create the tar with:"
  echo "  tar -czf ../nuevo_proyecto.tar.gz -C .. nuevo_proyecto"
  exit 1
fi

echo "Creando directorio remoto $REMOTE_PATH si no existe..."
ssh "$HOST" "mkdir -p '$REMOTE_PATH'"

echo "Copiando $TARFILE a $HOST:$REMOTE_PATH/ ..."
rsync -avz -e "ssh -o StrictHostKeyChecking=accept-new" "$TARFILE" "$HOST:$REMOTE_PATH/"

echo "Extrayendo en remoto..."
ssh "$HOST" "cd $REMOTE_PATH && tar -xzf $(basename $TARFILE) && rm -f $(basename $TARFILE) && echo 'Despliegue completado en $REMOTE_PATH'"

echo "Hecho. Si se pide contraseña, introdúcela en la terminal; para evitarlo configura una clave SSH."
