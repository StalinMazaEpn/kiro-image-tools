# Plan para migrar a uv (gestor moderno de Python)

Este plan detalla la migración del proyecto de pip/requirements.txt a uv, un gestor de paquetes Python moderno y rápido, sin dañar el proyecto actual.

## Análisis actual

**Estado actual:**
- `requirements.txt` con 14 dependencias fijas
- `Dockerfile` usa `pip install -r requirements.txt`
- `README.md` tiene instrucciones de `pip install -r requirements.txt`
- `docker-compose.yml` usa el Dockerfile actual

**Ventajas de uv:**
- 10-100x más rápido que pip
- Lock files determinísticos (pyproject.lock)
- Mejor resolución de dependencias
- Compatible con proyectos existentes
- Menor uso de memoria

## Plan de migración

### 1. Crear pyproject.toml

Crear `pyproject.toml` con las dependencias actuales de requirements.txt:

```toml
[project]
name = "image-tools"
version = "1.0.0"
description = "Image processing service with background removal"
requires-python = ">=3.11"
dependencies = [
    "azure-storage-blob==12.28.0",
    "flask-smorest==0.42.1",
    "Flask==2.3.3",
    "gunicorn==21.2.0",
    "ImageIO==2.37.3",
    "marshmallow==3.20.1",
    "numpy==1.26.4",
    "onnxruntime==1.20.1",
    "Pillow==10.1.0",
    "psutil==5.9.8",
    "PyMatting==1.1.15",
    "python-dotenv==1.0.0",
    "pytokens==0.4.1",
    "rembg==2.0.57",
    "requests==2.32.5",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 2. Migrar Dockerfile a uv

Actualizar `Dockerfile` para usar uv:

**Cambios:**
- Instalar uv en lugar de usar pip
- Usar `uv pip install` o `uv sync` para dependencias
- Mantener la estructura actual del Dockerfile

**Nuevo Dockerfile:**
```dockerfile
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

# Install uv
RUN pip install --no-cache-dir uv

# Copy pyproject.toml
COPY pyproject.toml .

# Install Python dependencies with uv
RUN uv pip install --system -r pyproject.toml

# Pre-descargar el modelo DURANTE el build
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
```

### 3. Actualizar README.md

**Cambios en sección "Local con Python (desarrollo)":**

```bash
# Instalar uv (una sola vez)
pip install uv

# Instalar dependencias con uv
uv pip install -r pyproject.toml

# Ejecutar servidor Flask en localhost:8070
python app.py
```

**Opcional: Agregar instrucciones de uv sync:**
```bash
# Usar uv sync (requiere virtualenv)
uv sync
python app.py
```

### 4. Mantener requirements.txt (opcional)

Mantener `requirements.txt` como fallback para compatibilidad. Puede generarse desde pyproject.toml:
```bash
uv pip compile pyproject.toml -o requirements.txt
```

### 5. Actualizar .gitignore

Agregar `uv.lock` si se usa `uv sync`:
```
# uv
uv.lock
.venv/

# HTTP requests
*.http
```

### 6. Crear archivo .http para pruebas de endpoints

Crear `api-tests.http` con ejemplos de requests para probar el endpoint `/image/image-process`:

```http
### Health check
GET http://localhost:8070/health

### Image process - Request básico
POST http://localhost:8070/api/v1/image/image-process
X-API-KEY: your-api-token-here
Content-Type: application/json

{
  "imageUrl": "https://example.com/original.png",
  "backgroundUrl": "https://example.com/background.png",
  "outputFilename": "resultado.png"
}

### Image process - Request completo con parámetros
POST http://localhost:8070/api/v1/image/image-process
X-API-KEY: your-api-token-here
Content-Type: application/json

{
  "imageUrl": "https://example.com/original.png",
  "backgroundUrl": "https://example.com/background.png",
  "outputFilename": "resultado.png",
  "scalePercent": 94,
  "minScalePercent": 20,
  "maxScalePercent": 100,
  "paddingPercent": 0,
  "horizontalAlign": "center",
  "verticalAlign": "bottom",
  "offsetX": 0,
  "offsetY": 0,
  "offsetUnit": "px"
}

### Download temp image
GET http://localhost:8070/api/v1/image/temp/<token>
```

## Archivos a modificar

### Crear
- `pyproject.toml` - Nuevo archivo de configuración de proyecto
- `api-tests.http` - Archivo con ejemplos de requests para probar endpoints

### Modificar
- `Dockerfile` - Usar uv en lugar de pip
- `README.md` - Actualizar instrucciones de instalación
- `.gitignore` - Agregar uv.lock, .venv y *.http

### Opcionales
- `requirements.txt` - Mantener como fallback o eliminar

## Verificación

**Pruebas a realizar:**
1. Build de Docker con nuevo Dockerfile
2. Ejecución local con uv
3. Tests funcionales
4. docker-compose funciona correctamente

**Rollback:**
- Si hay problemas, revertir Dockerfile a usar pip
- requirements.txt se mantiene como backup
