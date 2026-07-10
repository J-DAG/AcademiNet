import hashlib

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.database import get_cursor
from app.image_processing import optimizar_imagen
from app.models.schemas import ComentarioFotoCreate, FotografiaOut, InteraccionFoto, Respuesta

router = APIRouter(prefix="/fotografias", tags=["Fotografías"])

TIPOS_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGEN_BYTES = 25 * 1024 * 1024

_SELECT_META = """
    SELECT id_foto, id_usuario, nombre_archivo, tipo_mime, tamano_bytes,
           descripcion, fecha_subida, nro_likes,
           '/api/fotografias/' || id_foto || '/archivo' AS url_imagen,
           '/api/fotografias/' || id_foto || '/miniatura' AS url_miniatura
    FROM fotografias
"""


@router.post("/", response_model=FotografiaOut, status_code=201)
async def registrar_fotografia(
    id_usuario: int = Form(..., gt=0),
    descripcion: str | None = Form(None, max_length=1000),
    archivo: UploadFile = File(...),
):
    if archivo.content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(status_code=415, detail="Solo se permiten imágenes JPEG, PNG o WebP")
    contenido = await archivo.read(MAX_IMAGEN_BYTES + 1)
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    if len(contenido) > MAX_IMAGEN_BYTES:
        raise HTTPException(status_code=413, detail="La imagen supera el límite de 25 MB")

    try:
        optimizada = optimizar_imagen(contenido)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="El archivo no es una imagen válida") from exc

    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO fotografias
               (id_usuario, objeto, miniatura, nombre_archivo, tipo_mime, tipo_mime_miniatura, tamano_bytes, hash_sha256, descripcion)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (hash_sha256) WHERE hash_sha256 IS NOT NULL DO NOTHING
               RETURNING id_foto""",
            (id_usuario, optimizada.objeto, optimizada.miniatura, archivo.filename, "image/webp", "image/webp",
             len(optimizada.objeto), hashlib.sha256(contenido).hexdigest(), descripcion),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=409, detail="Esta imagen ya está almacenada")
        id_foto = row["id_foto"]
        cur.execute(_SELECT_META + " WHERE id_foto = %s", (id_foto,))
        return cur.fetchone()


@router.get("/", response_model=list[FotografiaOut])
def listar_fotografias(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    with get_cursor() as cur:
        cur.execute(_SELECT_META + " WHERE objeto IS NOT NULL ORDER BY fecha_subida DESC LIMIT %s OFFSET %s", (limit, offset))
        return cur.fetchall()


@router.get("/{id_foto}/archivo")
def obtener_archivo(id_foto: int):
    with get_cursor() as cur:
        cur.execute("SELECT objeto, tipo_mime, nombre_archivo FROM fotografias WHERE id_foto = %s", (id_foto,))
        row = cur.fetchone()
    if not row or row["objeto"] is None:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return Response(
        content=bytes(row["objeto"]),
        media_type=row["tipo_mime"] or "application/octet-stream",
        headers={"Cache-Control": "public, max-age=86400", "Content-Disposition": f'inline; filename="{row["nombre_archivo"] or "imagen"}"'},
    )


@router.get("/{id_foto}/miniatura")
def obtener_miniatura(id_foto: int):
    with get_cursor() as cur:
        cur.execute("SELECT COALESCE(miniatura, objeto) AS miniatura, COALESCE(tipo_mime_miniatura, tipo_mime) AS tipo_mime_miniatura FROM fotografias WHERE id_foto = %s", (id_foto,))
        row = cur.fetchone()
    if not row or row["miniatura"] is None:
        raise HTTPException(status_code=404, detail="Miniatura no encontrada")
    return Response(content=bytes(row["miniatura"]), media_type=row["tipo_mime_miniatura"] or "image/webp",
                    headers={"Cache-Control": "public, max-age=86400"})


@router.get("/{id_foto}", response_model=FotografiaOut)
def obtener_fotografia(id_foto: int):
    with get_cursor() as cur:
        cur.execute(_SELECT_META + " WHERE id_foto = %s AND objeto IS NOT NULL", (id_foto,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Fotografía no encontrada")
    return row


@router.get("/usuario/{id_usuario}", response_model=list[FotografiaOut])
def fotos_por_usuario(id_usuario: int):
    with get_cursor() as cur:
        cur.execute(_SELECT_META + " WHERE id_usuario = %s AND objeto IS NOT NULL ORDER BY fecha_subida DESC", (id_usuario,))
        return cur.fetchall()


@router.post("/{id_foto}/likes", response_model=Respuesta)
def dar_like_fotografia(id_foto: int, data: InteraccionFoto):
    with get_cursor() as cur:
        cur.execute("INSERT INTO likes_fotografias (id_foto, id_usuario) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING id_like_foto", (id_foto, data.id_usuario))
        if not cur.fetchone():
            raise HTTPException(status_code=409, detail="El usuario ya dio like a esta fotografía")
    return Respuesta(success=True, mensaje="Like registrado en la fotografía")


@router.post("/{id_foto}/comentarios", status_code=201)
def comentar_fotografia(id_foto: int, data: ComentarioFotoCreate):
    with get_cursor() as cur:
        cur.execute("INSERT INTO comentarios_foto (id_foto, id_usuario, contenido) VALUES (%s, %s, %s) RETURNING *", (id_foto, data.id_usuario, data.contenido))
        return cur.fetchone()
