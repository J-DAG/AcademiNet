"""Optimización uniforme de imágenes antes de almacenarlas en PostgreSQL."""

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps


@dataclass(frozen=True)
class ImagenOptimizada:
    objeto: bytes
    miniatura: bytes
    ancho: int
    alto: int


def _webp(imagen: Image.Image, calidad: int) -> bytes:
    salida = BytesIO()
    imagen.save(salida, format="WEBP", quality=calidad, method=4, optimize=True)
    return salida.getvalue()


def optimizar_imagen(contenido: bytes) -> ImagenOptimizada:
    """Corrige orientación, limita resolución y produce una miniatura ligera."""
    with Image.open(BytesIO(contenido)) as original:
        imagen = ImageOps.exif_transpose(original).convert("RGB")
        imagen.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
        objeto = _webp(imagen, 80)

        thumb = imagen.copy()
        thumb.thumbnail((320, 220), Image.Resampling.LANCZOS)
        miniatura = _webp(thumb, 72)
        return ImagenOptimizada(objeto, miniatura, imagen.width, imagen.height)
