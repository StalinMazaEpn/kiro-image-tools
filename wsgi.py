import os
from dotenv import load_dotenv
from app import create_app, setup_logging

load_dotenv()

# ==============================================
# CONFIGURACIÓN DE LOGGING
# ==============================================
setup_logging()

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8070))
    app.run(host="0.0.0.0", port=port)
