#!/usr/bin/env python3
"""
Script de prueba para validar la carga del modelo rembg
Ejecutar antes del despliegue para verificar que todo funciona correctamente.
"""

import time
import logging
import psutil
import os
from pathlib import Path

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_model_loading():
    """Testea la carga del modelo rembg"""
    logger.info("Iniciando test de carga del modelo...")
    
    # Medir memoria antes de cargar
    process = psutil.Process()
    memory_before = process.memory_info().rss / 1024 / 1024  # MB
    logger.info(f"Memoria antes de cargar: {memory_before:.1f} MB")
    
    # Medir tiempo de carga
    start_time = time.perf_counter()
    
    try:
        # Importar y cargar el modelo
        from app.model_manager import ModelManager
        
        # Forzar carga del modelo
        session = ModelManager.get_session()
        stats = ModelManager.stats()
        
        load_time = time.perf_counter() - start_time
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = memory_after - memory_before
        
        logger.info("Modelo cargado exitosamente!")
        logger.info(f"Tiempo de carga: {load_time:.2f} segundos")
        logger.info(f"Memoria usada: {memory_used:.1f} MB")
        logger.info(f"Memoria total: {memory_after:.1f} MB")
        logger.info(f"Stats del modelo: {stats}")
        
        # Test de remoción de fondo con una imagen dummy
        logger.info("Probando remoción de fondo...")
        test_remove_background(session)
        
        return True
        
    except Exception as e:
        logger.error(f"Error al cargar el modelo: {e}")
        return False

def test_remove_background(session):
    """Testea la función de remoción de fondo"""
    try:
        from PIL import Image
        from io import BytesIO
        import rembg
        
        # Crear una imagen de prueba simple (100x100px)
        test_image = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        test_image.save(buffer, format='PNG')
        buffer.seek(0)
        image_bytes = buffer.getvalue()
        
        # Probar remoción de fondo
        start_time = time.perf_counter()
        result_bytes = rembg.remove(image_bytes, session=session)
        process_time = time.perf_counter() - start_time
        
        logger.info(f"Remoción de fondo funcionó! Tiempo: {process_time:.3f}s")
        logger.info(f"Input: {len(image_bytes)} bytes → Output: {len(result_bytes)} bytes")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en remoción de fondo: {e}")
        return False

def main():
    """Función principal del test"""
    logger.info("Iniciando validación completa del sistema...")
    
    # Tests básicos
    tests = [
        ("Carga del modelo", test_model_loading),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\nEjecutando test: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Error en test {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumen
    logger.info("\n" + "="*50)
    logger.info("RESUMEN DE TESTS")
    logger.info("="*50)
    
    all_passed = True
    for test_name, passed in results:
        status = "PASÓ" if passed else "FALLÓ"
        logger.info(f"{test_name:.<30} {status}")
        if not passed:
            all_passed = False
    
    logger.info("="*50)
    if all_passed:
        logger.info("Todos los tests pasaron! El sistema está listo para despliegue.")
        return 0
    else:
        logger.error("Algunos tests fallaron. Revisa los errores antes de desplegar.")
        return 1

if __name__ == "__main__":
    exit(main())
