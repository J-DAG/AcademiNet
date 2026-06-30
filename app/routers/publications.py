from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    PublicacionCreate, PublicacionOut, ComentarioCreate, ComentarioOut,
    LikePublicacion, CitacionCreate, SimularFallo, Respuesta
)
from app.database import get_cursor

router = APIRouter(prefix="/publicaciones", tags=["Publicaciones"])

# SQL base para traer publicaciones con su foto adjunta
_SELECT_PUB = """
    SELECT p.id, p.titulo, p.tipo, p.autor, p.id_foto,
           f.ruta_imagen, p.fecha_publicacion, p.nro_citaciones,
           p.contenido, p.estado
    FROM publicaciones p
    LEFT JOIN fotografias f ON f.id_foto = p.id_foto
"""


@router.post("/", response_model=PublicacionOut)
def crear_publicacion(data: PublicacionCreate):
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO publicaciones (titulo, tipo, autor, contenido, id_foto) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (data.titulo, data.tipo, data.autor, data.contenido, data.id_foto)
        )
        new_id = cur.fetchone()["id"]
        cur.execute(_SELECT_PUB + " WHERE p.id = %s", (new_id,))
        return cur.fetchone()


@router.get("/", response_model=list[PublicacionOut])
def listar_publicaciones(limit: int = 20, offset: int = 0, tipo: str = None):
    with get_cursor() as cur:
        if tipo:
            cur.execute(
                _SELECT_PUB + " WHERE p.estado='activo' AND p.tipo=%s "
                "ORDER BY p.fecha_publicacion DESC LIMIT %s OFFSET %s",
                (tipo, limit, offset)
            )
        else:
            cur.execute(
                _SELECT_PUB + " WHERE p.estado='activo' "
                "ORDER BY p.fecha_publicacion DESC LIMIT %s OFFSET %s",
                (limit, offset)
            )
        return cur.fetchall()


@router.get("/{id_pub}", response_model=PublicacionOut)
def obtener_publicacion(id_pub: int):
    with get_cursor() as cur:
        cur.execute(_SELECT_PUB + " WHERE p.id = %s", (id_pub,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    return row


@router.delete("/{id_pub}", response_model=Respuesta)
def eliminar_publicacion(id_pub: int, id_usuario: int):
    with get_cursor() as cur:
        cur.execute("SELECT eliminar_publicacion(%s, %s)", (id_pub, id_usuario))
        resultado = cur.fetchone()["eliminar_publicacion"]
    if not resultado["success"]:
        raise HTTPException(status_code=400, detail=resultado["mensaje"])
    return Respuesta(success=True, mensaje=resultado["mensaje"])


# ── Comentarios ───────────────────────────────────────────────

@router.post("/{id_pub}/comentarios", response_model=ComentarioOut)
def agregar_comentario(id_pub: int, data: ComentarioCreate):
    data.id_publicacion = id_pub
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO comentarios (id_publicacion, id_usuario, contenido) "
            "VALUES (%s, %s, %s) RETURNING *",
            (data.id_publicacion, data.id_usuario, data.contenido)
        )
        return cur.fetchone()


@router.get("/{id_pub}/comentarios", response_model=list[ComentarioOut])
def listar_comentarios(id_pub: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM comentarios WHERE id_publicacion = %s "
            "ORDER BY fecha_comentario DESC",
            (id_pub,)
        )
        return cur.fetchall()


# ── Likes ─────────────────────────────────────────────────────

@router.post("/likes", response_model=Respuesta)
def dar_like(data: LikePublicacion):
    with get_cursor() as cur:
        cur.execute(
            "SELECT dar_like_publicacion(%s, %s)",
            (data.id_usuario, data.id_publicacion)
        )
        resultado = cur.fetchone()["dar_like_publicacion"]
    if not resultado["success"]:
        raise HTTPException(status_code=400, detail=resultado["mensaje"])
    return Respuesta(success=True, mensaje=resultado["mensaje"])


# ── Citaciones ────────────────────────────────────────────────

@router.post("/citaciones", response_model=Respuesta)
def citar_publicacion(data: CitacionCreate):
    with get_cursor() as cur:
        cur.execute(
            "SELECT citar_publicacion(%s, %s, %s)",
            (data.id_usuario, data.id_publicacion_origen, data.id_publicacion_destino)
        )
        resultado = cur.fetchone()["citar_publicacion"]
    if not resultado["success"]:
        raise HTTPException(status_code=400, detail=resultado["mensaje"])
    return Respuesta(success=True, mensaje=resultado["mensaje"])


# ── Simulación de fallo ACID ──────────────────────────────────

@router.post("/simular-fallo", response_model=Respuesta)
def simular_fallo(data: SimularFallo):
    with get_cursor() as cur:
        cur.execute(
            "SELECT simular_fallo_creditos(%s, %s, %s, %s)",
            (data.id_usuario_origen, data.id_usuario_destino,
             data.monto, data.forzar_fallo)
        )
        resultado = cur.fetchone()["simular_fallo_creditos"]
    return Respuesta(success=resultado["success"], mensaje=resultado["mensaje"])


# ── Consultas especiales ──────────────────────────────────────

@router.get("/consulta/top-fotografos")
def top_fotografos():
    with get_cursor() as cur:
        cur.execute("SELECT * FROM consulta_top_fotografos()")
        return cur.fetchall()


@router.get("/consulta/fotos-interacciones")
def fotos_interacciones():
    with get_cursor() as cur:
        cur.execute("SELECT * FROM consulta_fotos_mas_interacciones()")
        return cur.fetchall()
