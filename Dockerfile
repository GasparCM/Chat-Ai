FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de requisitos
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente y scripts
COPY telegram_ai.py .
COPY start.sh .
COPY historial.json .

# Crear directorio para sesiones de Telegram
RUN mkdir -p /app/sessions

# Hacer ejecutable el script de inicio
RUN chmod +x start.sh

# Comando por defecto
CMD ["./start.sh"]
