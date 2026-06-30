from pydantic import BaseModel, field_validator
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


# ── Fotografías ───────────────────────────────────────────────
class FotografiaCreate(BaseModel):
    id_usuario: int
    ruta_imagen: str
    descripcion: Optional[str] = None


class FotografiaOut(BaseModel):
    id_foto: int
    id_usuario: int
    ruta_imagen: str
    descripcion: Optional[str]
    fecha_subida: Optional[datetime]


# ── Publicaciones ─────────────────────────────────────────────
class PublicacionCreate(BaseModel):
    titulo: str
    tipo: str
    autor: int
    contenido: Optional[str] = None
    id_foto: Optional[int] = None       # FK opcional a fotografias

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
    id_foto: Optional[int]
    ruta_imagen: Optional[str]          # joined desde fotografias
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


class SeguirUsuario(BaseModel):
    id_seguidor: int
    id_seguido: int


class Respuesta(BaseModel):
    success: bool
    mensaje: str
    data: Optional[dict] = None
