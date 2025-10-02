#!/bin/bash

# Script de inicio para el bot de Telegram AI
echo "🚀 Iniciando Telegram AI Bot..."

# Verificar que las variables de entorno estén configuradas
if [ -z "$TELEGRAM_API_ID" ] || [ -z "$TELEGRAM_API_HASH" ] || [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "❌ Error: Variables de entorno faltantes"
    echo "Asegúrate de tener configuradas: TELEGRAM_API_ID, TELEGRAM_API_HASH, DEEPSEEK_API_KEY"
    exit 1
fi

# Crear directorio de sesiones si no existe
mkdir -p /app/sessions

# Ejecutar el bot
exec python telegram_ai.py
