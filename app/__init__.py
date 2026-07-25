from flask import Flask, jsonify
from flask_smorest import Api
from dotenv import load_dotenv
import os
import logging
import sys

load_dotenv()

logger = logging.getLogger(__name__)


def setup_logging():
    """
    Configura logging globalmente basado en variable de entorno LOG_LEVEL.
    Default: INFO
    Niveles válidos: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Validar nivel
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if log_level_str not in valid_levels:
        log_level_str = "INFO"
    
    log_level = getattr(logging, log_level_str)
    
    # Configurar basicConfig para mostrar en consola
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)  # Explícitamente a stdout
        ]
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    logger.info(f"Logging configurado con nivel: {log_level_str}")


def create_app():
    app = Flask(__name__)

    # Get dynamic global prefix
    global_prefix = os.getenv("IMAGE_TOOLS_API_GLOBAL_PREFIX", "/api/v1")
    # Asegurar que el prefijo siempre empiece con /
    if global_prefix and not global_prefix.startswith("/"):
        global_prefix = f"/{global_prefix}"

    # Flask-Smorest configuration
    app.config["API_TITLE"] = "Image Processing Tools API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.2"
    app.config["OPENAPI_URL_PREFIX"] = f"{global_prefix}/openapi"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/docs"
    app.config["OPENAPI_SWAGGER_UI_URL"] = (
        "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    )
    app.config["OPENAPI_SWAGGER_UI_EXPAND"] = True

    # Add security scheme configuration
    app.config["OPENAPI_SECURITY_SCHEMES"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-KEY",
            "description": "API key authentication",
        }
    }

    api = Api(app)

    # ─── Precarga del modelo al arrancar ────────────────────────
    # Se ejecuta una sola vez por proceso, ANTES de recibir requests.
    # En Gunicorn con --preload, se comparte entre workers (copy-on-write).
    # En Kubernetes, el pod estará listo para servir tráfico inmediatamente.
    _preload_model(app)

    # Import and register blueprints with dynamic prefix
    from app.routes.image import bp as image_bg
    from app.routes.health import health_bp

    # Register blueprints with flask-smorest and dynamic prefix
    api.register_blueprint(image_bg, url_prefix=global_prefix)
    app.register_blueprint(health_bp, url_prefix=global_prefix)

    # Root health endpoint
    @app.route("/", methods=["GET"])
    def health():
        environment = os.environ.get("ENVIRONMENT", "development")
        return jsonify(
            {
                "message": "Image Processing Tools API is running",
                "environment": environment,
                "status": "success",
            }
        )

    return app


def _preload_model(app) -> None:
    """Carga el modelo fuera de request context."""
    from app.model_manager import ModelManager
    with app.app_context():
        try:
            ModelManager.get_session()
            logger.info("[MODEL] Modelo precargado exitosamente")
        except Exception as e:
            logger.error(f"[MODEL] Falló la precarga: {e}")
            # En producción puedes hacer raise para que el pod no arranque
