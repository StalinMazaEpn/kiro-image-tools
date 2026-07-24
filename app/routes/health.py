import psutil
from flask import Blueprint, jsonify
from app.model_manager import ModelManager

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health():
    """Liveness probe básico — el pod está vivo."""
    return jsonify({"status": "ok"}), 200


@health_bp.route("/health/model", methods=["GET"])
def model_status():
    """
    Readiness probe — el pod está listo para recibir tráfico.
    K8s solo enviará requests cuando este endpoint devuelva 200.
    """
    stats = ModelManager.stats()
    if not stats["ready"]:
        return jsonify({"status": "loading", **stats}), 503

    mem = psutil.Process().memory_info().rss / 1024 / 1024
    return jsonify({
        "status": "ready",
        "memory_mb": round(mem, 1),
        **stats,
    }), 200
