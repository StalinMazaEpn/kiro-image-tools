# Use Python 3.11 slim image
FROM python:3.11-slim
 
# Set working directory
WORKDIR /app
 
ENV PYTHONPATH=/app \
    U2NET_HOME=/app/models \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*
 
# Copy requirements first for better caching
COPY requirements.txt .
 
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-descargar el modelo DURANTE el build
# El modelo queda en /app/models/u2net.onnx dentro de la imagen.
# Ningún pod descargará nada en tiempo de ejecución.
RUN mkdir -p /app/models && \
    python -c "from rembg import new_session; new_session('u2net')" && \
    echo "[BUILD] Modelo descargado correctamente"
 
# Copy application code
COPY . .
 
# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app
 
# Expose port
EXPOSE 8070
 
# Run the application with --preload to share model between workers
CMD ["gunicorn", "--bind", "0.0.0.0:8070", \
     "--workers", "2", \
     "--preload", \
     "--timeout", "300", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "wsgi:app"]
 
# BUILD: docker build -t image-tools:v1 .
# RUN: docker run --env-file ./.env -it -p 8070:8070 --name image-tools image-tools:v1