from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime, date
import re


# ── Usuarios ──────────────────────────────────────────────────
class UsuarioCreate(BaseModel):
    cedula: str
    apellidos: str
    nombres: str
    cargo: str
    email: Optional[str] = None
    fecha_nac: Optional[date] = None
    tipo_cuenta: str = "regular"
    privacidad: str = "publico"

    @field_validator("cargo")
    @classmethod
    def cargo_valido(cls, v):
        if v not in ("profesor", "investigador"):
            raise ValueError("cargo debe ser 'profesor' o 'investigador'")
        return v

    @field_validator("cedula")
    @classmethod
    def cedula_valida(cls, v):
        if not re.match(r"^\d{10,13}$", v):
            raise ValueError("cédula debe tener entre 10 y 13 dígitos")
        return v


class UsuarioOut(BaseModel):
    id_usuario: int
    cedula: str
    apellidos: str
    nombres: str
    cargo: str
    email: Optional[str]
    created_at: Optional[datetime]


# ── Cuentas ───────────────────────────────────────────────────
class CuentaOut(BaseModel):
    id_cuenta: int
    id_usuario: int
    tipo: str
    fecha_creacion: datetime
    numero_seguidores: int
    privacidad: str
    estado: str
    bio: Optional[str]
    creditos: int


class CuentaUpdate(BaseModel):
    tipo: Optional[str] = None
    privacidad: Optional[str] = None
    estado: Optional[str] = None
    bio: Optional[str] = None


# ── Publicaciones ─────────────────────────────────────────────
class PublicacionCreate(BaseModel):
    titulo: str
    tipo: str
    autor: int
    contenido: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v):
        if v not in ("paper", "microblog", "comentario"):
            raise ValueError("tipo debe ser 'paper', 'microblog' o 'comentario'")
        return v


class PublicacionOut(BaseModel):
    id: int
    titulo: str
    tipo: str
    autor: int
    fecha_publicacion: datetime
    nro_citaciones: int
    contenido: Optional[str]
    estado: str


# ── Comentarios ───────────────────────────────────────────────
class ComentarioCreate(BaseModel):
    id_publicacion: int
    id_usuario: int
    contenido: str


class ComentarioOut(BaseModel):
    id_comentario: int
    id_publicacion: int
    id_usuario: int
    contenido: str
    fecha_comentario: datetime


# ── Fotografías ───────────────────────────────────────────────
class FotografiaOut(BaseModel):
    id_foto: int
    id_usuario: int
    descripcion: Optional[str]
    nro_likes: int
    fecha_subida: Optional[datetime]
    ruta_imagen: Optional[str]


# ── Acciones ──────────────────────────────────────────────────
class LikePublicacion(BaseModel):
    id_usuario: int
    id_publicacion: int


class CitacionCreate(BaseModel):
    id_usuario: int
    id_publicacion_origen: int
    id_publicacion_destino: int


class SimularFallo(BaseModel):
    id_usuario_origen: int
    id_usuario_destino: int
    monto: int
    forzar_fallo: bool = False


# ── Seguir usuario ────────────────────────────────────────────
class SeguirUsuario(BaseModel):
    id_seguidor: int
    id_seguido: int


# ── Respuesta genérica ────────────────────────────────────────
class Respuesta(BaseModel):
    success: bool
    mensaje: str
    data: Optional[dict] = None
