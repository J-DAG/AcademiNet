from pydantic import BaseModel, Field, field_validator
from typing import Literal
from typing import Optional
from datetime import datetime, date
import re


# ── Usuarios ──────────────────────────────────────────────────
class UsuarioCreate(BaseModel):
    cedula: str
    apellidos: str = Field(min_length=1, max_length=100)
    nombres: str = Field(min_length=1, max_length=100)
    cargo: Literal["profesor", "investigador"]
    email: Optional[str] = None
    fecha_nac: Optional[date] = None
    tipo_cuenta: Literal["regular", "premium"] = "regular"
    privacidad: Literal["publico", "privado"] = "publico"

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
    tipo: Optional[Literal["regular", "premium"]] = None
    privacidad: Optional[Literal["publico", "privado"]] = None
    estado: Optional[Literal["activo", "inactivo"]] = None
    bio: Optional[str] = Field(default=None, max_length=1000)


# ── Fotografías ───────────────────────────────────────────────
class FotografiaOut(BaseModel):
    id_foto: int
    id_usuario: int
    nombre_archivo: Optional[str]
    tipo_mime: Optional[str]
    tamano_bytes: Optional[int]
    url_imagen: str
    url_miniatura: str
    descripcion: Optional[str]
    fecha_subida: Optional[datetime]


# ── Publicaciones ─────────────────────────────────────────────
class PublicacionCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=255)
    tipo: Literal["paper", "microblog", "comentario"]
    autor: int = Field(gt=0)
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
    ruta_imagen: Optional[str]          # endpoint que entrega el BYTEA
    fecha_publicacion: datetime
    nro_citaciones: int
    contenido: Optional[str]
    estado: str
    total_likes: int = 0
    total_comentarios: int = 0


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
    monto: int = Field(gt=0)
    forzar_fallo: bool = False


class SeguirUsuario(BaseModel):
    id_seguidor: int
    id_seguido: int


class Respuesta(BaseModel):
    success: bool
    mensaje: str
    data: Optional[dict] = None
