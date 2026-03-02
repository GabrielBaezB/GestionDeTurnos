#!/bin/bash

# ==============================================================================
# Script de Despliegue Automatizado - GestionDeTurnos
# Compatible con: Ubuntu 20.04 / 22.04 / 24.04 y Debian 11/12
# ==============================================================================

set -e # Detener el script si hay algún error

echo "======================================================"
echo "🚀 Iniciando instalación automatizada de GestionDeTurnos"
echo "======================================================"

# 1. Comprobar permisos de superusuario (root)
if [ "$EUID" -ne 0 ]; then
  echo "❌ Por favor, ejecuta este script como root (usando sudo)"
  exit 1
fi

# 2. Actualizar el sistema e instalar dependencias básicas
echo "Actualizando paquetes del sistema..."
apt-get update -y
apt-get install -y ca-certificates curl gnupg git nano ufw

# 3. Instalar Docker si no está instalado
if ! command -v docker &> /dev/null; then
    echo "🐳 Docker no encontrado. Instalando Docker..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Configurar el repositorio de Docker
    source /etc/os-release
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $VERSION_CODENAME stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
    echo "✅ Docker ya está instalado."
fi

# Activar Docker para que inicie con el sistema
systemctl enable docker
systemctl start docker

# 4. Clonar el repositorio si no estamos dentro de él
REPO_DIR="/opt/GestionDeTurnos"

if [ ! -d "$REPO_DIR" ]; then
    echo "📥 Clonando el repositorio en $REPO_DIR..."
    git clone https://github.com/GabrielBaezB/GestionDeTurnos.git $REPO_DIR
    cd $REPO_DIR
else
    echo "✅ El repositorio ya existe en $REPO_DIR. Actualizando..."
    cd $REPO_DIR
    git pull origin main
fi

# 5. Configurar Variables de Entorno
if [ ! -f ".env" ]; then
    echo "⚙️ Configurando archivo .env a partir de .env.example..."
    cp .env.example .env
    echo "⚠️ ATENCIÓN: Se ha creado un archivo .env con contraseñas por defecto."
    echo "Es *altamente recomendado* que edites /opt/GestionDeTurnos/.env cambiando DEFAULT_ADMIN_PASSWORD y POSTGRES_PASSWORD antes de ir a producción."
else
    echo "✅ Archivo .env existente detectado."
fi

# 6. Levantar los contenedores de producción
echo "🏗️ Levantando contenedores Core (Base de Datos, Redis, Backend API)..."
docker compose up -d

echo "======================================================"
echo "✨ ¡Instalación Completada! ✨"
echo "======================================================"
echo "Tus servicios ya están corriendo."
echo "Puedes comprobar el estado con: cd /opt/GestionDeTurnos && docker compose ps"
echo ""
echo "Si esto es un Servidor Local (Intranet), accede en los navegadores usando la IP Privada del PC http://<tu-ip>:8000/kiosk"
echo "Si esto es un Servidor Público (VPS), te recomendamos usar Nginx/Traefik para agregar SSL/HTTPS."
