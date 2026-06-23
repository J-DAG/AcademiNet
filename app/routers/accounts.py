from fastapi import APIRouter, HTTPException
from app.models.schemas import CuentaOut, CuentaUpdate, Respuesta
from app.database import get_cursor

router = APIRouter(prefix="/cuentas", tags=["Cuentas"])


@router.get("/{id_usuario}", response_model=CuentaOut)
def obtener_cuenta(id_usuario: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM cuentas WHERE id_usuario = %s",
            (id_usuario,)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return row


@router.patch("/{id_usuario}", response_model=CuentaOut)
def actualizar_cuenta(id_usuario: int, data: CuentaUpdate):
    campos = {k: v for k, v in data.model_dump().items() if v is not None}
    if not campos:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")

    set_clause = ", ".join(f"{k} = %s" for k in campos)
    valores = list(campos.values()) + [id_usuario]

    with get_cursor() as cur:
        cur.execute(
            f"UPDATE cuentas SET {set_clause} WHERE id_usuario = %s RETURNING *",
            valores
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return row


@router.get("/{id_usuario}/creditos")
def obtener_creditos(id_usuario: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT creditos, numero_seguidores FROM cuentas WHERE id_usuario = %s",
            (id_usuario,)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return row


@router.get("/{id_usuario}/auditoria")
def auditoria_usuario(id_usuario: int, limit: int = 20):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM auditoria WHERE id_usuario = %s "
            "ORDER BY fecha_evento DESC LIMIT %s",
            (id_usuario, limit)
        )
        return cur.fetchall()
