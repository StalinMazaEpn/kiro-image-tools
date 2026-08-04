import logging
import os
import secrets
import tempfile
import threading
from pathlib import Path
from io import BytesIO
from urllib.parse import unquote, urlparse
from datetime import datetime, timedelta, timezone
from flask import jsonify, send_file, url_for
from flask_smorest import Blueprint as SmorestBlueprint
from app.schemas.image import (
    ImageProcessRequestSchema,
    ImageProcessResponseSchema,
    RemoveBackgroundRequestSchema,
    RemoveBackgroundResponseSchema,
    ErrorResponseSchema,
)
from PIL import Image
from dotenv import load_dotenv
from app.middleware.auth import verify_token
import requests

load_dotenv()

# Crear blueprint
bp = SmorestBlueprint("image", __name__, description="Image service operations")

# Configuración
ALLOWED_EXTENSIONS = {".png", ".jpeg", ".jpg"}

try:
    MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "10"))
except ValueError:
    MAX_UPLOAD_MB = 10

VALIDATE_HTTPS_URL = (
    os.environ.get("IMAGE_PROCESS_VALIDATE_HTTPS_URL", "false").lower() == "true"
)

PUBLIC_IMAGE_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/png,image/jpeg,image/gif,image/bmp,image/tiff,image/*;q=0.9",
    "Connection": "keep-alive",
}

# Solo se aceptan respuestas declaradas como imagen.
ALLOWED_IMAGE_MIME_TYPES = {
    "image/avif",
    "image/bmp",
    "image/gif",
    "image/heic",
    "image/heif",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/tiff",
    "image/webp",
}

MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
try:
    TEMP_FILE_TTL_MINUTES = int(os.environ.get("IMAGE_PROCESS_TEMP_TTL_MINUTES", "15"))
except ValueError:
    TEMP_FILE_TTL_MINUTES = 15

TEMP_OUTPUT_DIR = Path(tempfile.gettempdir()) / "image-tools" / "image-process"
TEMP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_FILES = {}
TEMP_FILES_LOCK = threading.Lock()


class PublicImageDownloadError(Exception):
    """Error al descargar una imagen pública."""


class PublicImageTooLargeError(Exception):
    """Imagen pública excede el tamaño permitido."""


def _validate_https_url(url: str, field_name: str) -> None:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            f"{field_name} debe ser una URL pública válida (http/https)."
        )

    if VALIDATE_HTTPS_URL and scheme != "https":
        raise ValueError(
            f"{field_name} debe ser una URL HTTPS pública válida."
        )


def _download_public_image(url: str, field_name: str) -> bytes:
    _validate_https_url(url, field_name)

    try:
        response = requests.get(
            url,
            timeout=120,
            headers=PUBLIC_IMAGE_REQUEST_HEADERS,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectTimeout:
        raise PublicImageDownloadError(
            f"{field_name}: tiempo de espera agotado al intentar conectar con el servidor. "
            f"Verifica que la URL sea accesible públicamente."
        )
    except requests.exceptions.ReadTimeout:
        raise PublicImageDownloadError(
            f"{field_name}: el servidor tardó demasiado en responder. "
            f"Intenta de nuevo más tarde o verifica que la URL esté disponible."
        )
    except requests.exceptions.SSLError as exc:
        raise PublicImageDownloadError(
            f"{field_name}: error de certificado SSL al conectar con el servidor ({exc}). "
            f"Verifica que la URL use un certificado válido."
        )
    except requests.exceptions.ConnectionError as exc:
        raise PublicImageDownloadError(
            f"{field_name}: no se pudo establecer conexión con el servidor. "
            f"Verifica que la URL sea accesible desde internet ({exc})."
        )
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "desconocido"
        status_messages = {
            400: "solicitud inválida (400 Bad Request). Verifica que la URL sea correcta.",
            401: "acceso no autorizado (401 Unauthorized). La imagen requiere autenticación.",
            403: "acceso denegado (403 Forbidden). La imagen no es de acceso público.",
            404: "imagen no encontrada (404 Not Found). Verifica que la URL exista.",
            429: "demasiadas solicitudes (429 Too Many Requests). Intenta más tarde.",
            500: "error interno del servidor de origen (500). Intenta más tarde.",
            502: "error de gateway en el servidor de origen (502). Intenta más tarde.",
            503: "servicio del servidor de origen no disponible (503). Intenta más tarde.",
        }
        detail = status_messages.get(status_code, f"error HTTP {status_code}.")
        raise PublicImageDownloadError(
            f"{field_name}: {detail}"
        ) from exc
    except requests.exceptions.TooManyRedirects:
        raise PublicImageDownloadError(
            f"{field_name}: la URL genera demasiadas redirecciones. "
            f"Verifica que la URL sea directa y accesible."
        )
    except requests.RequestException as exc:
        raise PublicImageDownloadError(
            f"{field_name}: error inesperado al descargar la imagen ({exc})."
        ) from exc

    content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if (not content_type.startswith("image/")) or (
        content_type not in ALLOWED_IMAGE_MIME_TYPES
    ):
        raise PublicImageDownloadError(
            f"{field_name}: la URL no devuelve un tipo de contenido de imagen permitido (Content-Type: {content_type or 'desconocido'})."
        )

    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            if int(content_length) > MAX_UPLOAD_BYTES:
                raise PublicImageTooLargeError(
                    f"{field_name} supera el tamaño máximo permitido de {MAX_UPLOAD_MB} MB."
                )
        except ValueError:
            logging.warning("Content-Length inválido en %s", field_name)

    file_bytes = response.content
    if not file_bytes:
        raise PublicImageDownloadError(
            f"{field_name} está vacío o no contiene datos."
        )

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise PublicImageTooLargeError(
            f"{field_name} supera el tamaño máximo permitido de {MAX_UPLOAD_MB} MB."
        )

    try:
        with BytesIO(file_bytes) as bio:
            with Image.open(bio) as img:
                img.verify()
    except Exception as exc:
        raise PublicImageDownloadError(
            f"{field_name} no es una imagen válida."
        ) from exc

    return file_bytes


def _normalize_output_filename(filename: str) -> str:
    clean_name = (filename or "").strip()
    if not clean_name:
        return "image-process-output.png"

    stem = Path(clean_name).stem
    if not stem:
        stem = "image-process-output"

    return f"{stem}.png"


def _cleanup_expired_temp_files(now_utc: datetime | None = None) -> None:
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    with TEMP_FILES_LOCK:
        expired_tokens = [
            token
            for token, metadata in TEMP_FILES.items()
            if metadata["expires_at"] <= now_utc
        ]

        for token in expired_tokens:
            metadata = TEMP_FILES.pop(token, None)
            if not metadata:
                continue
            file_path = metadata.get("path")
            if file_path and file_path.exists():
                try:
                    file_path.unlink()
                except OSError:
                    logging.warning("No se pudo eliminar archivo temporal: %s", file_path)


def _store_temp_output_image(image_bytes: bytes, output_filename: str):
    _cleanup_expired_temp_files()

    safe_filename = _normalize_output_filename(output_filename)
    token = secrets.token_urlsafe(24)
    disk_filename = f"{token}_{safe_filename}"
    file_path = TEMP_OUTPUT_DIR / disk_filename

    with open(file_path, "wb") as temp_file:
        temp_file.write(image_bytes)

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=TEMP_FILE_TTL_MINUTES)

    with TEMP_FILES_LOCK:
        TEMP_FILES[token] = {
            "path": file_path,
            "download_name": safe_filename,
            "expires_at": expires_at,
        }

    return token, safe_filename, expires_at


def _resolve_scale_params(scale_percent, min_scale_percent, max_scale_percent):
    scale_percent = float(scale_percent)
    min_scale_percent = float(min_scale_percent)
    max_scale_percent = float(max_scale_percent)

    if min_scale_percent > max_scale_percent:
        min_scale_percent, max_scale_percent = max_scale_percent, min_scale_percent

    applied_scale = max(min_scale_percent, min(scale_percent, max_scale_percent))
    return applied_scale, min_scale_percent, max_scale_percent


def _resolve_aligned_position(
    usable_origin,
    usable_size,
    item_size,
    align,
):
    if align in {"left", "top"}:
        return usable_origin
    if align in {"right", "bottom"}:
        return usable_origin + max(0, usable_size - item_size)
    return usable_origin + max(0, (usable_size - item_size) // 2)


def _remove_background(image):
    """Remueve el fondo de una imagen usando rembg"""
    from app.model_manager import ModelManager
    import rembg

    session = ModelManager.get_session()
    return rembg.remove(image, session=session)


def process_image_to_background(
    file_bytes,
    background_bytes,
    scale_percent=94.0,
    min_scale_percent=20.0,
    max_scale_percent=100.0,
    padding_percent=0.0,
    horizontal_align="center",
    vertical_align="center",
    offset_x=0.0,
    offset_y=0.0,
    offset_unit="px",
):
    """Procesa una imagen removiendo su fondo, escalándola dinámicamente y centrándola sobre un fondo."""
    try:
        with BytesIO(file_bytes) as input_bio, BytesIO(background_bytes) as bg_bio:
            with Image.open(input_bio) as input_img:
                input_image = input_img.convert("RGBA")
            with Image.open(bg_bio) as bg_img:
                background_image = bg_img.convert("RGBA")

        image_no_bg = _remove_background(input_image)

        bbox = image_no_bg.getbbox()
        if bbox:
            subject_image = image_no_bg.crop(bbox)
        else:
            subject_image = image_no_bg

        bg_width, bg_height = background_image.size
        subject_width, subject_height = subject_image.size

        if subject_width <= 0 or subject_height <= 0:
            raise ValueError("La imagen sin fondo no tiene dimensiones válidas.")

        padding_percent = float(padding_percent)
        safe_padding_percent = max(0.0, min(40.0, padding_percent))
        horizontal_padding = int(bg_width * (safe_padding_percent / 100.0))
        vertical_padding = int(bg_height * (safe_padding_percent / 100.0))

        usable_width = max(1, bg_width - (horizontal_padding * 2))
        usable_height = max(1, bg_height - (vertical_padding * 2))

        fit_factor = min(usable_width / subject_width, usable_height / subject_height)
        fit_width = max(1, int(subject_width * fit_factor))
        fit_height = max(1, int(subject_height * fit_factor))

        (
            applied_scale_percent,
            applied_min_scale_percent,
            applied_max_scale_percent,
        ) = _resolve_scale_params(scale_percent, min_scale_percent, max_scale_percent)

        scaled_width = max(1, int(fit_width * (applied_scale_percent / 100.0)))
        scaled_height = max(1, int(fit_height * (applied_scale_percent / 100.0)))

        # Clamp final: nunca exceder el área útil del fondo.
        clamp_factor = min(usable_width / scaled_width, usable_height / scaled_height, 1.0)
        final_width = max(1, int(scaled_width * clamp_factor))
        final_height = max(1, int(scaled_height * clamp_factor))

        resized_subject = subject_image.resize((final_width, final_height), Image.LANCZOS)

        output_image = background_image.copy()
        usable_left = horizontal_padding
        usable_top = vertical_padding
        usable_right = usable_left + usable_width
        usable_bottom = usable_top + usable_height

        base_x = _resolve_aligned_position(
            usable_left,
            usable_width,
            final_width,
            (horizontal_align or "center").lower(),
        )
        base_y = _resolve_aligned_position(
            usable_top,
            usable_height,
            final_height,
            (vertical_align or "center").lower(),
        )

        if (offset_unit or "px").lower() == "percent":
            computed_offset_x = int((usable_width * float(offset_x)) / 100.0)
            computed_offset_y = int((usable_height * float(offset_y)) / 100.0)
        else:
            computed_offset_x = int(float(offset_x))
            computed_offset_y = int(float(offset_y))

        min_x = usable_left
        max_x = max(usable_left, usable_right - final_width)
        min_y = usable_top
        max_y = max(usable_top, usable_bottom - final_height)

        center_x = max(min_x, min(base_x + computed_offset_x, max_x))
        center_y = max(min_y, min(base_y + computed_offset_y, max_y))

        output_image.paste(resized_subject, (center_x, center_y), resized_subject)

        render_metadata = {
            "background_size": {"width": bg_width, "height": bg_height},
            "subject_bbox": {
                "left": bbox[0] if bbox else 0,
                "top": bbox[1] if bbox else 0,
                "right": bbox[2] if bbox else subject_width,
                "bottom": bbox[3] if bbox else subject_height,
            },
            "padding_percent": round(safe_padding_percent, 2),
            "usable_area_size": {"width": usable_width, "height": usable_height},
            "fit_subject_size": {"width": fit_width, "height": fit_height},
            "scale_requested_percent": round(float(scale_percent), 2),
            "scale_applied_percent": round(applied_scale_percent, 2),
            "scale_bounds": {
                "min": round(applied_min_scale_percent, 2),
                "max": round(applied_max_scale_percent, 2),
            },
            "output_subject_size": {"width": final_width, "height": final_height},
            "alignment": {
                "horizontal": (horizontal_align or "center").lower(),
                "vertical": (vertical_align or "center").lower(),
            },
            "offset": {
                "x": round(float(offset_x), 2),
                "y": round(float(offset_y), 2),
                "unit": (offset_unit or "px").lower(),
                "applied_x_px": computed_offset_x,
                "applied_y_px": computed_offset_y,
            },
            "position": {"x": center_x, "y": center_y},
        }

        try:
            if isinstance(resized_subject, Image.Image):
                resized_subject.close()
        except Exception:
            pass

        try:
            if isinstance(subject_image, Image.Image) and subject_image is not image_no_bg:
                subject_image.close()
        except Exception:
            pass

        try:
            if isinstance(image_no_bg, Image.Image):
                image_no_bg.close()
        except Exception:
            pass

        try:
            input_image.close()
        except Exception:
            pass

        try:
            background_image.close()
        except Exception:
            pass

        return output_image, render_metadata

    except Exception as e:
        logging.error(f"Ocurrió un error durante el procesamiento genérico: {e}")
        return None, None


@bp.get("/image/health")
@bp.doc(security=[])
def health():
    """Health check endpoint for image service"""
    return jsonify(
        {
            "message": "Image service is healthy",
            "status": "success",
            "service": "image",
        }
    )


@bp.post("/image/image-process")
@bp.doc(
    security=[{"ApiKeyAuth": []}],
    summary="Procesar imagen con fondo dinámico",
    description="Descarga dos imágenes por URL HTTPS pública, remueve el fondo de la imagen original, la centra sobre la imagen de fondo y retorna una URL temporal para descarga.",
)
@bp.arguments(ImageProcessRequestSchema)
@bp.response(200, ImageProcessResponseSchema)
@bp.response(400, ErrorResponseSchema)
@bp.response(401, ErrorResponseSchema)
@bp.response(413, ErrorResponseSchema)
@bp.response(500, ErrorResponseSchema)
@bp.response(502, ErrorResponseSchema)
@verify_token
def imageprocess(request_data):
    """Endpoint genérico para remover fondo y centrar sobre fondo dinámico."""

    image_url = request_data.get("imageUrl")
    background_url = request_data.get("backgroundUrl")
    output_filename = request_data.get("outputFilename")
    scale_percent = request_data.get("scalePercent", 94.0)
    min_scale_percent = request_data.get("minScalePercent", 20.0)
    max_scale_percent = request_data.get("maxScalePercent", 100.0)
    padding_percent = request_data.get("paddingPercent", 0.0)
    horizontal_align = request_data.get("horizontalAlign", "center")
    vertical_align = request_data.get("verticalAlign", "center")
    offset_x = request_data.get("offsetX", 0.0)
    offset_y = request_data.get("offsetY", 0.0)
    offset_unit = request_data.get("offsetUnit", "px")
    logging.info(f"Using the following parameters for image generation: scalePercent={scale_percent}, minScalePercent={min_scale_percent}, maxScalePercent={max_scale_percent}, paddingPercent={padding_percent}, horizontalAlign={horizontal_align}, verticalAlign={vertical_align}, offsetX={offset_x}, offsetY={offset_y}, offsetUnit={offset_unit}")

    if not image_url or not background_url or not output_filename:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "'imageUrl', 'backgroundUrl' y 'outputFilename' son obligatorios.",
                    "success": False,
                }
            ),
            400,
        )

    try:
        original_bytes = _download_public_image(image_url, "imageUrl")
        background_bytes = _download_public_image(background_url, "backgroundUrl")
    except ValueError as exc:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": str(exc),
                    "success": False,
                }
            ),
            400,
        )
    except PublicImageTooLargeError as exc:
        return (
            jsonify(
                {
                    "error": "Payload Too Large",
                    "message": str(exc),
                    "success": False,
                }
            ),
            413,
        )
    except PublicImageDownloadError as exc:
        return (
            jsonify(
                {
                    "error": "Bad Gateway",
                    "message": str(exc),
                    "success": False,
                }
            ),
            502,
        )

    processed_image, render_metadata = process_image_to_background(
        original_bytes,
        background_bytes,
        scale_percent=scale_percent,
        min_scale_percent=min_scale_percent,
        max_scale_percent=max_scale_percent,
        padding_percent=padding_percent,
        horizontal_align=horizontal_align,
        vertical_align=vertical_align,
        offset_x=offset_x,
        offset_y=offset_y,
        offset_unit=offset_unit,
    )
    if processed_image is None:
        return (
            jsonify(
                {
                    "error": "Internal Server Error",
                    "message": "No se pudo procesar la imagen con el fondo proporcionado.",
                    "success": False,
                }
            ),
            500,
        )

    try:
        output_buffer = BytesIO()
        processed_image.save(output_buffer, format="PNG")
        output_bytes = output_buffer.getvalue()
    except Exception as exc:
        logging.exception("Error serializando la imagen procesada")
        return (
            jsonify(
                {
                    "error": "Internal Server Error",
                    "message": f"Error al generar la imagen de salida: {exc}",
                    "success": False,
                }
            ),
            500,
        )
    finally:
        try:
            output_buffer.close()
        except Exception:
            pass
        try:
            processed_image.close()
        except Exception:
            pass

    token, safe_filename, expires_at = _store_temp_output_image(
        output_bytes, output_filename
    )
    download_url = url_for("image.download_temp_image", token=token, _external=True)

    return (
        jsonify(
            {
                "success": True,
                "message": "Imagen procesada correctamente. Usa la URL temporal para descargar el archivo.",
                "filename": safe_filename,
                "content_type": "image/png",
                "download_url": download_url,
                "expires_at": expires_at.isoformat(),
                "render_metadata": render_metadata,
            }
        ),
        200,
    )


@bp.post("/image/remove-background")
@bp.doc(
    security=[{"ApiKeyAuth": []}],
    summary="Remover fondo de imagen",
    description="Descarga una imagen por URL pública, remueve el fondo usando U2NET y retorna una URL temporal para descargar la imagen sin fondo con sus dimensiones originales.",
)
@bp.arguments(RemoveBackgroundRequestSchema)
@bp.response(200, RemoveBackgroundResponseSchema)
@bp.response(400, ErrorResponseSchema)
@bp.response(401, ErrorResponseSchema)
@bp.response(413, ErrorResponseSchema)
@bp.response(500, ErrorResponseSchema)
@bp.response(502, ErrorResponseSchema)
@verify_token
def remove_background(request_data):
    """Endpoint para remover fondo de una imagen y devolver resultado con dimensiones originales."""

    image_url = request_data.get("imageUrl")
    output_filename = request_data.get("outputFilename", "removed-bg.png")

    if not image_url:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "'imageUrl' es obligatorio.",
                    "success": False,
                }
            ),
            400,
        )

    try:
        original_bytes = _download_public_image(image_url, "imageUrl")
    except ValueError as exc:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": str(exc),
                    "success": False,
                }
            ),
            400,
        )
    except PublicImageTooLargeError as exc:
        return (
            jsonify(
                {
                    "error": "Payload Too Large",
                    "message": str(exc),
                    "success": False,
                }
            ),
            413,
        )
    except PublicImageDownloadError as exc:
        return (
            jsonify(
                {
                    "error": "Bad Gateway",
                    "message": str(exc),
                    "success": False,
                }
            ),
            502,
        )

    try:
        with BytesIO(original_bytes) as input_bio:
            with Image.open(input_bio) as input_img:
                input_image = input_img.convert("RGBA")
                original_width, original_height = input_image.size

        image_no_bg = _remove_background(input_image)

        output_buffer = BytesIO()
        image_no_bg.save(output_buffer, format="PNG")
        output_bytes = output_buffer.getvalue()
    except Exception as exc:
        logging.exception("Error al remover fondo de la imagen")
        return (
            jsonify(
                {
                    "error": "Internal Server Error",
                    "message": f"No se pudo remover el fondo de la imagen: {exc}",
                    "success": False,
                }
            ),
            500,
        )
    finally:
        try:
            output_buffer.close()
        except Exception:
            pass
        try:
            image_no_bg.close()
        except Exception:
            pass
        try:
            input_image.close()
        except Exception:
            pass

    token, safe_filename, expires_at = _store_temp_output_image(
        output_bytes, output_filename
    )
    download_url = url_for("image.download_temp_image", token=token, _external=True)

    return (
        jsonify(
            {
                "success": True,
                "message": "Fondo removido correctamente. Usa la URL temporal para descargar el archivo.",
                "filename": safe_filename,
                "content_type": "image/png",
                "download_url": download_url,
                "expires_at": expires_at.isoformat(),
                "original_size": {
                    "width": original_width,
                    "height": original_height,
                },
            }
        ),
        200,
    )


@bp.get("/image/temp/<token>")
@bp.doc(
    security=[],
    summary="Descargar imagen temporal",
    description="Descarga el resultado temporal generado por image-process mediante token.",
)
def download_temp_image(token):
    _cleanup_expired_temp_files()

    with TEMP_FILES_LOCK:
        metadata = TEMP_FILES.get(token)

    if not metadata:
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": "El archivo temporal no existe o ya expiró.",
                    "success": False,
                }
            ),
            404,
        )

    file_path = metadata["path"]
    if not file_path.exists():
        with TEMP_FILES_LOCK:
            TEMP_FILES.pop(token, None)
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": "El archivo temporal no está disponible.",
                    "success": False,
                }
            ),
            404,
        )

    return send_file(
        file_path,
        mimetype="image/png",
        as_attachment=True,
        download_name=metadata["download_name"],
        max_age=0,
    )
