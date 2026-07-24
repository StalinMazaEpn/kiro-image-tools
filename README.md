# Introduction 
Este proyecto implementa una solución optimizada para la remoción de fondos en imágenes usando el modelo U2NET y la librería rembg. La imagen final es una imagen con fondo transparente colocada sobre un fondo establecido en una imagen plantilla.

## Arquitectura Implementada

### 1. **ModelManager** (`app/model_manager.py`)
- Singleton thread-safe para la sesión rembg
- Double-checked locking para concurrencia
- Estadísticas de carga (tiempo, estado)
- Logging detallado del proceso

### 2. **Precarga en App** (`app/__init__.py`)
- `_preload_model()` durante `create_app()`
- Compartido entre workers con `--preload`
- Manejo de errores en startup

### 3. **Health Checks** (`app/routes/health.py`)
- `/health` - Liveness probe básico
- `/health/model` - Readiness probe con estado del modelo
- Métricas de memoria y tiempo de carga

### 4. **Docker Optimizado** (`Dockerfile`)
- `U2NET_HOME=/app/models` - Ruta fija
- Descarga del modelo durante el **build**
- `--preload` en Gunicorn para compartir entre workers
- Modelo embebido, sin descargas en runtime

### Test del Modelo
```bash
# Verificar carga del modelo localmente
python test_model_loading.py
```

**Expected output:**
```
Modelo cargado exitosamente!
Tiempo de carga: 1.8 segundos
Memoria usada: 420.5 MB
Memoria total: 480.2 MB
Probando remoción de fondo...
Remoción de fondo funcionó! Tiempo: 0.245s
Todos los tests pasaron!
```

```bash
# Construir imagen con modelo embebido
docker build -t image-tools:test .

# Verificar que el modelo está en la imagen
docker run --rm image-tools:test ls -lh /app/models/
# Expected: u2net.onnx 176M
```
## Construir y ejecutar

### Local con Python (desarrollo)

```bash
# Activar entorno virtual
.\venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor Flask en localhost:8070
python app.py

# Con LOG_LEVEL personalizado
$env:LOG_LEVEL="DEBUG"; python app.py
```

### Docker (sin Compose)

```bash
# BUILD: 
docker build -t image-tools:v1 .

# RUN: 
docker run --env-file .env -it -p 8070:8070 --name image-tools image-tools:v1
```

### Docker Compose (recomendado para desarrollo local)

```bash
# Levantar servicio en background
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f image-tools

# Apagar servicio
docker-compose down

# Reconstruir imagen (si hay cambios en requirements.txt o Dockerfile)
docker-compose up -d --build

# Ejecutar tests dentro del contenedor
docker-compose exec image-tools python -m unittest discover -s tests -p "test_*.py" -v
```

**Características del docker-compose:**
- ✅ Lee variables desde `.env` automáticamente (FTP, Azure, tokens, etc.)
- ✅ No deja valores sensibles hardcodeados
- ✅ Cachea modelo U2NET en volumen persistente
- ✅ Health check cada 10s para verificar disponibilidad
- ✅ Accesible en `http://localhost:8070`
- ✅ Logs disponibles con `docker-compose logs`

### Deployment en Kubernetes (AKS)

**Variables de configuración requeridas en el ConfigMap `image-tools-configmap`:**

```yaml
IMAGE_TOOLS_API_GLOBAL_PREFIX: "/api/v1"
IMAGE_TOOLS_API_TOKENS: "<comma-separated-tokens>"
FTP_HOST: "ftp.example.com"
FTP_PATH: "/signatures"
MAX_UPLOAD_MB: "10"
IMAGE_PROCESS_VALIDATE_HTTPS_URL: "true"  # Recomendado en producción
LOG_LEVEL: "INFO"
```

**Secretos en `image-tools-configmap-secret`:**

```yaml
FTP_USER: "<user>"
FTP_PASS: "<password>"
AZURE_BLOB_STORAGE_CONNECTION_STRING: "<connection-string>"
```

**Notas de seguridad:**
- ✅ `IMAGE_PROCESS_VALIDATE_HTTPS_URL=true` en producción (rechaza URLs HTTP inseguras)
- ✅ `IMAGE_PROCESS_VALIDATE_HTTPS_URL=false` en desarrollo local (permite testing)
- ✅ Valores sensibles (FTP_PASS, Azure conn string) en Secrets, no en ConfigMap
- ✅ Los tokens de API nunca se exponen en logs (logging sanitizado)

## Nuevo endpoint genérico: image-process

Permite procesar una imagen original y centrarla sobre un fondo dinámico enviado por URL.

- Autenticación: header `X-API-KEY`
- Método: `POST`
- Ruta: `/api/v1/image/image-process`

### Request básico:

```json
{
	"imageUrl": "https://example.com/original.png",
	"backgroundUrl": "https://example.com/background.png",
	"outputFilename": "resultado.png"
}
```

### Request completo con parámetros dinámicos:

```json
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
```

**Parámetros dinámicos:**
- `scalePercent` (default: 94) - Escala aplicada al sujeto (1-300%)
- `minScalePercent` / `maxScalePercent` - Rango válido de escala (default: 20-100%)
- `paddingPercent` (default: 0) - Padding alrededor del área útil (0-40%)
- `horizontalAlign` (default: "center") - left|center|right
- `verticalAlign` (default: "center") - top|center|bottom
- `offsetX` / `offsetY` (default: 0) - Desplazamiento adicional desde posición alineada
- `offsetUnit` (default: "px") - px|percent

### Comportamiento:
- Descarga ambas imágenes desde URLs HTTPS públicas.
- Remueve el fondo de `imageUrl` usando el flujo de rembg/U2NET ya existente.
- Centra el sujeto sobre `backgroundUrl` aplicando escala, padding y alineación.
- Guarda el resultado en carpeta temporal del servidor (TTL: 15 min).
- Devuelve una URL temporal para descargar el archivo desde navegador.

### Respuesta exitosa:

```json
{
	"success": true,
	"message": "Imagen procesada correctamente. Usa la URL temporal para descargar el archivo.",
	"filename": "resultado.png",
	"content_type": "image/png",
	"download_url": "http://localhost:8070/api/v1/image/temp/<token>",
	"expires_at": "2026-05-07T15:30:00+00:00",
	"render_metadata": {
		"background_size": {"width": 800, "height": 600},
		"padding_percent": 0,
		"usable_area_size": {"width": 800, "height": 600},
		"scale_applied_percent": 94,
		"alignment": {"horizontal": "center", "vertical": "bottom"},
		"offset": {"x": 0, "y": 0, "unit": "px"},
		"position": {"x": 200, "y": 400}
	}
}
```

# Ejecutar Tests

Los tests unitarios validan la funcionalidad del endpoint `image-process` incluyendo casos edge para escala, padding, alineación y offsets.

## Requisitos previos

```bash
# Activar entorno virtual
.\venv\Scripts\Activate.ps1
```

## Ejecutar todos los tests

```bash
# Mostrar resultado resumido
python -m unittest discover -s tests -p "test_*.py"

# Mostrar resultado detallado (verbose)
python -m unittest discover -s tests -p "test_*.py" -v
```

## Ejecutar solo tests de image-process

```bash
python -m unittest discover -s tests -p "test_image_process.py" -v
```

## Tests disponibles

- `test_image_process_returns_download_url` - Happy path básico con parámetros default
- `test_image_process_requires_api_key` - Validación de autenticación
- `test_image_process_rejects_non_https_url_when_enabled` - Validación de HTTPS
- `test_image_process_rejects_large_remote_file` - Límite de tamaño (MAX_UPLOAD_MB)
- `test_image_process_clamps_scale_to_max` - Escala respeta maxScalePercent
- `test_image_process_padding_reduces_subject_size` - Padding reduce el área útil
- `test_image_process_center_bottom_alignment` - Alineación vertical bottom + horizontal center
- `test_image_process_percent_offset_is_applied` - Offset en porcentaje se calcula correctamente

## Output esperado

```
test_image_process_center_bottom_alignment ... ok
test_image_process_clamps_scale_to_max ... ok
test_image_process_padding_reduces_subject_size ... ok
test_image_process_percent_offset_is_applied ... ok
test_image_process_rejects_large_remote_file ... ok
test_image_process_rejects_non_https_url_when_enabled ... ok
test_image_process_requires_api_key ... ok
test_image_process_returns_download_url ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.860s

OK
```

## Configuración de Logging durante tests

El logging se configura automáticamente con nivel **INFO** por default. Para cambiar durante tests:

```bash
# DEBUG: Ver todos los mensajes de logging
$env:LOG_LEVEL="DEBUG"
python -m unittest discover -s tests -p "test_image_process.py" -v

# WARNING: Solo advertencias y errores
$env:LOG_LEVEL="WARNING"
python -m unittest discover -s tests -p "test_image_process.py" -v

# Resetear a default (INFO)
Remove-Item env:LOG_LEVEL -ErrorAction SilentlyContinue
```

# Build and Test
TODO: Describe and show how to build your code and run the tests. 

# Contribute
TODO: Explain how other users and developers can contribute to make your code better. 

If you want to learn more about creating good readme files then refer the following [guidelines](https://docs.microsoft.com/en-us/azure/devops/repos/git/create-a-readme?view=azure-devops). You can also seek inspiration from the below readme files:
- [ASP.NET Core](https://github.com/aspnet/Home)
- [Visual Studio Code](https://github.com/Microsoft/vscode)
- [Chakra Core](https://github.com/Microsoft/ChakraCore)