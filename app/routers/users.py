from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import UsuarioCreate, UsuarioOut, SeguirUsuario, Respuesta
from app.database import get_cursor

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/", response_model=Respuesta)
def crear_usuario(data: UsuarioCreate):
    with get_cursor() as cur:
        cur.execute(
            "SELECT registrar_usuario_y_cuenta(%s,%s,%s,%s,%s,%s,%s)",
            (data.cedula, data.apellidos, data.nombres, data.cargo,
             data.email, data.tipo_cuenta, data.privacidad)
        )
        resultado = cur.fetchone()["registrar_usuario_y_cuenta"]
    if not resultado["success"]:
        raise HTTPException(status_code=400, detail=resultado["mensaje"])
    return Respuesta(success=True, mensaje=resultado["mensaje"],
                     data={"id_usuario": resultado.get("id_usuario"),
                           "id_cuenta": resultado.get("id_cuenta")})


@router.get("/", response_model=list[UsuarioOut])
def listar_usuarios(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_usuario, cedula, apellidos, nombres, cargo, email, created_at "
            "FROM usuarios ORDER BY id_usuario LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return cur.fetchall()


@router.get("/{id_usuario}", response_model=UsuarioOut)
def obtener_usuario(id_usuario: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_usuario, cedula, apellidos, nombres, cargo, email, created_at "
            "FROM usuarios WHERE id_usuario = %s",
            (id_usuario,)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return row


@router.post("/seguir", response_model=Respuesta)
def seguir_usuario(data: SeguirUsuario):
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO seguidores (id_seguidor, id_seguido) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (data.id_seguidor, data.id_seguido)
        )
    return Respuesta(success=True, mensaje="Ahora sigues a este usuario.")


@router.delete("/seguir", response_model=Respuesta)
def dejar_de_seguir(data: SeguirUsuario):
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM seguidores WHERE id_seguidor = %s AND id_seguido = %s",
            (data.id_seguidor, data.id_seguido)
        )
    return Respuesta(success=True, mensaje="Dejaste de seguir al usuario.")


@router.get("/consulta/activos")
def profesores_activos():
    with get_cursor() as cur:
        cur.execute("SELECT * FROM consulta_profesores_activos()")
        return cur.fetchall()
