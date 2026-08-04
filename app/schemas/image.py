from marshmallow import Schema, fields, validate

# Schemas para documentación
class ImageProcessRequestSchema(Schema):
    """Schema para el request de procesamiento de imagen con fondo dinámico.

    Descarga dos imágenes desde URLs públicas, remueve el fondo de la imagen original
    usando el modelo U2NET, y la compone sobre la imagen de fondo aplicando escalado,
    padding, alineación y offset configurables.
    """

    imageUrl = fields.Str(
        required=True,
        metadata={
            "description": "URL pública (HTTP/HTTPS) de la imagen original a la que se le removerá el fondo. "
            "Formatos soportados: PNG, JPEG, JPG. Tamaño máximo configurable por MAX_UPLOAD_MB (default: 10 MB).",
            "example": "https://example.com/producto.png",
        },
    )
    backgroundUrl = fields.Str(
        required=True,
        metadata={
            "description": "URL pública (HTTP/HTTPS) de la imagen de fondo sobre la cual se compondrá el sujeto. "
            "Las dimensiones de esta imagen definen el canvas final de salida.",
            "example": "https://example.com/fondo-800x600.png",
        },
    )
    outputFilename = fields.Str(
        required=True,
        metadata={
            "description": "Nombre sugerido para el archivo de salida. La extensión siempre será .png "
            "independientemente de lo que se indique aquí.",
            "example": "resultado-final.png",
        },
    )
    scalePercent = fields.Float(
        required=False,
        load_default=94.0,
        validate=validate.Range(min=1, max=300),
        metadata={
            "description": "Porcentaje de escalado aplicado sobre el tamaño base de encaje (fit). "
            "El tamaño de encaje es el mayor tamaño que el sujeto puede alcanzar sin exceder el área útil "
            "del fondo, manteniendo su proporción original. "
            "Valores: 100 = ocupa todo el área útil, 50 = ocupa la mitad. "
            "El valor final se clampea entre minScalePercent y maxScalePercent.",
            "example": 80.0,
        },
    )
    minScalePercent = fields.Float(
        required=False,
        load_default=20.0,
        validate=validate.Range(min=1, max=300),
        metadata={
            "description": "Límite inferior del rango de escalado. Si scalePercent es menor que este valor, "
            "se usará minScalePercent como escala aplicada. Si minScalePercent > maxScalePercent, "
            "se intercambian automáticamente.",
            "example": 20.0,
        },
    )
    maxScalePercent = fields.Float(
        required=False,
        load_default=100.0,
        validate=validate.Range(min=1, max=300),
        metadata={
            "description": "Límite superior del rango de escalado. Si scalePercent es mayor que este valor, "
            "se usará maxScalePercent como escala aplicada. Fórmula: "
            "applied_scale = max(minScalePercent, min(scalePercent, maxScalePercent)).",
            "example": 100.0,
        },
    )
    paddingPercent = fields.Float(
        required=False,
        load_default=0.0,
        validate=validate.Range(min=0, max=40),
        metadata={
            "description": "Porcentaje de padding por lado aplicado sobre las dimensiones del fondo. "
            "Define un margen interno que reduce el 'área útil' disponible para posicionar el sujeto. "
            "Ejemplo: con paddingPercent=10 y fondo de 1000x1000px, se aplican 100px por lado, "
            "resultando en un área útil de 800x800px. Se clampea internamente a [0, 40].",
            "example": 5.0,
        },
    )
    horizontalAlign = fields.Str(
        required=False,
        load_default="center",
        validate=validate.OneOf(["left", "center", "right"]),
        metadata={
            "description": "Alineación horizontal del sujeto dentro del área útil. "
            "'left' = pegado al borde izquierdo, 'center' = centrado, 'right' = pegado al borde derecho. "
            "Se aplica antes del offset.",
            "example": "center",
        },
    )
    verticalAlign = fields.Str(
        required=False,
        load_default="center",
        validate=validate.OneOf(["top", "center", "bottom"]),
        metadata={
            "description": "Alineación vertical del sujeto dentro del área útil. "
            "'top' = pegado arriba, 'center' = centrado, 'bottom' = pegado abajo. "
            "Se aplica antes del offset.",
            "example": "bottom",
        },
    )
    offsetX = fields.Float(
        required=False,
        load_default=0.0,
        validate=validate.Range(min=-10000, max=10000),
        metadata={
            "description": "Desplazamiento horizontal adicional aplicado después de la alineación. "
            "Valores positivos mueven el sujeto hacia la derecha, negativos hacia la izquierda. "
            "La unidad depende de offsetUnit (px o percent del área útil). "
            "La posición final se clampea para que el sujeto no salga del área útil.",
            "example": 0.0,
        },
    )
    offsetY = fields.Float(
        required=False,
        load_default=0.0,
        validate=validate.Range(min=-10000, max=10000),
        metadata={
            "description": "Desplazamiento vertical adicional aplicado después de la alineación. "
            "Valores positivos mueven el sujeto hacia abajo, negativos hacia arriba. "
            "La unidad depende de offsetUnit (px o percent del área útil). "
            "La posición final se clampea para que el sujeto no salga del área útil.",
            "example": 0.0,
        },
    )
    offsetUnit = fields.Str(
        required=False,
        load_default="px",
        validate=validate.OneOf(["px", "percent"]),
        metadata={
            "description": "Unidad en la que se interpretan offsetX y offsetY. "
            "'px' = píxeles absolutos; 'percent' = porcentaje del área útil "
            "(ej: offsetX=10 con unit='percent' y área útil de 800px = 80px de desplazamiento).",
            "example": "px",
        },
    )


class ImageProcessResponseSchema(Schema):
    """Schema para la respuesta exitosa del procesamiento de imagen.

    Incluye una URL temporal para descargar el resultado y metadatos
    detallados sobre el cálculo de escalado, posición y composición.
    """

    success = fields.Bool(
        metadata={"description": "Indica si la operación fue exitosa (siempre true en respuesta 200)"}
    )
    message = fields.Str(
        metadata={"description": "Mensaje descriptivo del resultado de la operación"}
    )
    filename = fields.Str(
        metadata={"description": "Nombre del archivo generado (siempre con extensión .png)"}
    )
    content_type = fields.Str(
        metadata={"description": "Tipo MIME del contenido generado (siempre image/png)"}
    )
    download_url = fields.Str(
        metadata={
            "description": "URL temporal para descargar la imagen procesada. "
            "Expira según IMAGE_PROCESS_TEMP_TTL_MINUTES (default: 15 min). "
            "No requiere autenticación.",
            "example": "http://localhost:8070/api/v1/image/temp/abc123token",
        }
    )
    expires_at = fields.Str(
        metadata={
            "description": "Fecha y hora de expiración de la URL temporal en formato ISO 8601 (UTC).",
            "example": "2026-05-07T15:30:00+00:00",
        }
    )
    render_metadata = fields.Dict(
        metadata={
            "description": "Metadatos detallados del procesamiento: tamaño del fondo, bbox del sujeto, "
            "padding aplicado, área útil, tamaño de encaje, escala solicitada vs aplicada, "
            "límites de escala, tamaño final del sujeto, alineación, offset y posición final en px."
        }
    )


class RemoveBackgroundRequestSchema(Schema):
    """Schema para el request de remoción de fondo simple.

    Descarga una imagen desde URL pública, remueve el fondo usando U2NET,
    y retorna la imagen resultante con sus dimensiones originales intactas.
    """

    imageUrl = fields.Str(
        required=True,
        metadata={
            "description": "URL pública (HTTP/HTTPS) de la imagen a la que se le removerá el fondo. "
            "Formatos soportados: PNG, JPEG, JPG. Tamaño máximo configurable por MAX_UPLOAD_MB (default: 10 MB).",
            "example": "https://example.com/producto.png",
        },
    )
    outputFilename = fields.Str(
        required=False,
        load_default="removed-bg.png",
        metadata={
            "description": "Nombre sugerido para el archivo de salida. La extensión siempre será .png.",
            "example": "producto-sin-fondo.png",
        },
    )


class RemoveBackgroundResponseSchema(Schema):
    """Schema para la respuesta exitosa de remoción de fondo."""

    success = fields.Bool(
        metadata={"description": "Indica si la operación fue exitosa (siempre true en respuesta 200)"}
    )
    message = fields.Str(
        metadata={"description": "Mensaje descriptivo del resultado de la operación"}
    )
    filename = fields.Str(
        metadata={"description": "Nombre del archivo generado (siempre con extensión .png)"}
    )
    content_type = fields.Str(
        metadata={"description": "Tipo MIME del contenido generado (siempre image/png)"}
    )
    download_url = fields.Str(
        metadata={
            "description": "URL temporal para descargar la imagen sin fondo. "
            "Expira según IMAGE_PROCESS_TEMP_TTL_MINUTES (default: 15 min). "
            "No requiere autenticación.",
            "example": "http://localhost:8070/api/v1/image/temp/abc123token",
        }
    )
    expires_at = fields.Str(
        metadata={
            "description": "Fecha y hora de expiración de la URL temporal en formato ISO 8601 (UTC).",
            "example": "2026-05-07T15:30:00+00:00",
        }
    )
    original_size = fields.Dict(
        metadata={
            "description": "Dimensiones originales de la imagen (width, height en px).",
            "example": {"width": 800, "height": 600},
        }
    )


class ErrorResponseSchema(Schema):
    """Schema para respuestas de error (400, 401, 413, 500, 502)"""

    error = fields.Str(
        metadata={
            "description": "Tipo de error HTTP (Bad Request, Unauthorized, Payload Too Large, Internal Server Error, Bad Gateway)"
        }
    )
    message = fields.Str(
        metadata={
            "description": "Mensaje descriptivo del error con detalles sobre la causa y posibles soluciones"
        }
    )
    success = fields.Bool(
        metadata={"description": "Siempre false para respuestas de error"}
    )
