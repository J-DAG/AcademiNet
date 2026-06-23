from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.models.schemas import FotografiaOut, Respuesta
from app.database import get_cursor

router = APIRouter(prefix="/fotografias", tags=["Fotografías"])


@router.post("/", response_model=FotografiaOut)
async def subir_fotografia(
    id_usuario: int = Form(...),
    descripcion: str = Form(""),
    imagen: UploadFile = File(...)
):
    contenido = await imagen.read()
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO fotografias (id_usuario, objeto, descripcion) "
            "VALUES (%s, %s, %s) RETURNING id_foto, id_usuario, descripcion, nro_likes, fecha_subida, ruta_imagen",
            (id_usuario, contenido, descripcion)  # psycopg3 acepta bytes directamente
        )
        return cur.fetchone()


@router.get("/", response_model=list[FotografiaOut])
def listar_fotografias(limit: int = 20, offset: int = 0):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_foto, id_usuario, descripcion, nro_likes, fecha_subida, ruta_imagen "
            "FROM fotografias ORDER BY fecha_subida DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return cur.fetchall()


@router.get("/usuario/{id_usuario}", response_model=list[FotografiaOut])
def fotos_por_usuario(id_usuario: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_foto, id_usuario, descripcion, nro_likes, fecha_subida, ruta_imagen "
            "FROM fotografias WHERE id_usuario = %s ORDER BY fecha_subida DESC",
            (id_usuario,)
        )
        return cur.fetchall()


@router.post("/{id_foto}/like", response_model=Respuesta)
def dar_like_foto(id_foto: int, id_usuario: int):
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO likes_fotografias (id_foto, id_usuario) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (id_foto, id_usuario)
        )
    return Respuesta(success=True, mensaje="Like registrado en fotografía.")


@router.post("/{id_foto}/comentarios", response_model=Respuesta)
def comentar_foto(id_foto: int, id_usuario: int, contenido: str):
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO comentarios_foto (id_foto, id_usuario, contenido) VALUES (%s, %s, %s)",
            (id_foto, id_usuario, contenido)
        )
    return Respuesta(success=True, mensaje="Comentario agregado a la fotografía.")
