import os
from dotenv import load_dotenv

load_dotenv()
# Dynamic global prefix configuration
GLOBAL_PREFIX = os.getenv("IMAGE_TOOLS_API_GLOBAL_PREFIX", "/api/v1")

# Environment configuration
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
PORT = int(os.environ.get("PORT", 8070))

# API Documentation Settings
API_TITLE = "Image Processing Tools API"
API_VERSION = "v1"
OPENAPI_VERSION = "3.0.2"
OPENAPI_DESCRIPTION = "La API está documentada siguiendo el estándar OpenAPI 3.0, implementada mediante flask-smorest y esquemas de validación con marshmallow."
