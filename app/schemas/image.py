from marshmallow import Schema, fields, validate

# Schemas para documentación
class ImageBannerRequestSchema(Schema):
    """Schema para el request de creación de banner"""
    filename = fields.Str(
        required=True,
        metadata={"description": "Nombre del archivo de imagen"},
    )
    storageImagePath = fields.Str(
        required=True,
        metadata={
            "description": "Ruta del imagen en Azure Blob Storage (container/ruta/blob o URL completa)"
        },
    )


class ImageProcessRequestSchema(Schema):
    """Schema para el request de procesamiento genérico de imagen"""
    imageUrl = fields.Str(
        required=True,
        metadata={"description": "URL HTTPS pública de la imagen original"},
    )
    backgroundUrl = fields.Str(
        required=True,
        metadata={"description": "URL HTTPS pública de la imagen de fondo"},
    )
    outputFilename = fields.Str(
        required=True,
        metadata={
            "description": "Nombre del archivo de salida sugerido por el cliente"
        },
    )
    scalePercent = fields.Float(
        required=False,
        load_default=94.0,
        validate=validate.Range(min=1, max=300),
        metadata={
            "description": "Porcentaje de escalado aplicado sobre el tamaño base de encaje"
        },
    )
    minScalePercent = fields.Float(
        required=False,
        load_default=20.0,
        validate=validate.Range(min=1, max=300),
        metadata={"description": "Límite mínimo permitido para scalePercent"},
    )
    maxScalePercent = fields.Float(
        required=False,
        load_default=100.0,
        validate=validate.Range(min=1, max=300),
        metadata={"description": "Límite máximo permitido para scalePercent"},
    )
    paddingPercent = fields.Float(
        required=False,
        load_default=0.0,
        validate=validate.Range(min=0, max=40),
        metadata={
            "description": "Padding por lado sobre el fondo para calcular el área útil"
        },
    )
    horizontalAlign = fields.Str(
        required=False,
        load_default="center",
        validate=validate.OneOf(["left", "center", "right"]),
        metadata={"description": "Alineación horizontal del sujeto"},
    )
    verticalAlign = fields.Str(
        required=False,
        load_default="center",
        validate=validate.OneOf(["top", "center", "bottom"]),
        metadata={"description": "Alineación vertical del sujeto"},
    )
    offsetX = fields.Float(
        required=False,
        load_default=0.0,
        validate=validate.Range(min=-10000, max=10000),
        metadata={"description": "Ajuste horizontal adicional"},
    )
    offsetY = fields.Float(
        required=False,
        load_default=0.0,
        validate=validate.Range(min=-10000, max=10000),
        metadata={"description": "Ajuste vertical adicional"},
    )
    offsetUnit = fields.Str(
        required=False,
        load_default="px",
        validate=validate.OneOf(["px", "percent"]),
        metadata={"description": "Unidad de offset: px o percent"},
    )


class ImageBannerResponseSchema(Schema):
    """Schema para la respuesta exitosa"""
    filename = fields.Str(metadata={"description": "Nombre del archivo procesado"})
    content_type = fields.Str(
        metadata={"description": "Tipo de contenido del archivo"}
    )
    metadata = fields.Dict(metadata={"description": "Metadata original del request"})
    message = fields.Str(metadata={"description": "Mensaje de éxito"})
    success = fields.Bool(
        metadata={"description": "Indica si la operación fue exitosa"}
    )


class ImageProcessResponseSchema(Schema):
    """Schema para la respuesta de procesamiento con URL temporal"""
    success = fields.Bool(
        metadata={"description": "Indica si la operación fue exitosa"}
    )
    message = fields.Str(metadata={"description": "Mensaje descriptivo"})
    filename = fields.Str(metadata={"description": "Nombre del archivo generado"})
    content_type = fields.Str(metadata={"description": "Tipo de contenido generado"})
    download_url = fields.Str(
        metadata={"description": "URL temporal para descargar la imagen"}
    )
    expires_at = fields.Str(
        metadata={"description": "Fecha de expiración de la URL temporal en ISO8601"}
    )
    render_metadata = fields.Dict(
        metadata={
            "description": "Detalles de cálculo de escalado y composición de la imagen"
        }
    )


class ErrorResponseSchema(Schema):
    """Schema para respuestas de error"""
    error = fields.Str(metadata={"description": "Tipo de error"})
    message = fields.Str(metadata={"description": "Mensaje descriptivo del error"})
    success = fields.Bool(metadata={"description": "Siempre false para errores"})
