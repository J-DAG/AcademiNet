from fastapi import APIRouter, HTTPException
from app.models.schemas import FotografiaCreate, FotografiaOut
from app.database import get_cursor

router = APIRouter(prefix="/fotografias", tags=["Fotografías"])


@router.post("/", response_model=FotografiaOut)
def registrar_fotografia(data: FotografiaCreate):
    """Registra una fotografía por URL (enlace raw de GitHub)."""
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO fotografias (id_usuario, ruta_imagen, descripcion) "
            "VALUES (%s, %s, %s) "
            "RETURNING id_foto, id_usuario, ruta_imagen, descripcion, fecha_subida",
            (data.id_usuario, data.ruta_imagen, data.descripcion)
        )
        return cur.fetchone()


@router.get("/", response_model=list[FotografiaOut])
def listar_fotografias(limit: int = 20, offset: int = 0):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_foto, id_usuario, ruta_imagen, descripcion, fecha_subida "
            "FROM fotografias ORDER BY fecha_subida DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return cur.fetchall()


@router.get("/{id_foto}", response_model=FotografiaOut)
def obtener_fotografia(id_foto: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_foto, id_usuario, ruta_imagen, descripcion, fecha_subida "
            "FROM fotografias WHERE id_foto = %s",
            (id_foto,)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Fotografía no encontrada.")
    return row


@router.get("/usuario/{id_usuario}", response_model=list[FotografiaOut])
def fotos_por_usuario(id_usuario: int):
    """Fotografías registradas por un usuario (pueden estar en varias publicaciones)."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_foto, id_usuario, ruta_imagen, descripcion, fecha_subida "
            "FROM fotografias WHERE id_usuario = %s ORDER BY fecha_subida DESC",
            (id_usuario,)
        )
        return cur.fetchall()
