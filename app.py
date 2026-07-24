import os
from app import create_app, setup_logging

# ==============================================
# CONFIGURACIÓN DE LOGGING
# ==============================================
setup_logging()

# Create Flask app
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8070))
    app.run(host="0.0.0.0", port=port)
