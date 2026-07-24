import threading
import logging
import time
import os

logger = logging.getLogger(__name__)

class ModelManager:
    """
    Singleton thread-safe para la sesión rembg.
    Garantiza que el modelo se cargue UNA sola vez,
    sin importar cuántos workers o threads inicien.
    """
    _session = None
    _lock = threading.Lock()
    _load_time: float = 0.0
    _ready: bool = False

    @classmethod
    def get_session(cls, model_name: str = "u2net"):
        if cls._session is None:
            with cls._lock:
                if cls._session is None:   # double-checked locking
                    cls._load()
        return cls._session

    @classmethod
    def _load(cls, model_name: str = "u2net"):
        from rembg import new_session
        logger.info("[MODEL] Iniciando carga del modelo '%s'...", model_name)
        t0 = time.perf_counter()
        try:
            cls._session = new_session(model_name)
            cls._load_time = round(time.perf_counter() - t0, 2)
            cls._ready = True
            logger.info("[MODEL] Listo en %.2f s", cls._load_time)
        except Exception as exc:
            logger.exception("[MODEL] Error al cargar el modelo: %s", exc)
            raise

    @classmethod
    def is_ready(cls) -> bool:
        return cls._ready

    @classmethod
    def stats(cls) -> dict:
        return {
            "ready": cls._ready,
            "load_time_seconds": cls._load_time,
            "model": "u2net",
        }
