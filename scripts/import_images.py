"""Importa de forma reanudable las imágenes locales de ./imagenes como BYTEA."""

import hashlib
import mimetypes
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import close_pool, get_cursor, init_db

IMAGE_DIR = ROOT / "imagenes"
EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES = 25 * 1024 * 1024


def importar() -> None:
    init_db()
    archivos = sorted(p for p in IMAGE_DIR.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONES)
    with get_cursor() as cur:
        cur.execute("SELECT id_usuario FROM usuarios ORDER BY id_usuario")
        usuarios = [row["id_usuario"] for row in cur.fetchall()]
    if not usuarios:
        raise RuntimeError("No existen usuarios. Inicializa y puebla usuarios antes de importar imágenes.")

    insertadas = omitidas = demasiado_grandes = 0
    for indice, ruta in enumerate(archivos):
        contenido = ruta.read_bytes()
        if len(contenido) > MAX_BYTES:
            demasiado_grandes += 1
            continue
        digest = hashlib.sha256(contenido).hexdigest()
        mime = mimetypes.guess_type(ruta.name)[0] or "application/octet-stream"
        with get_cursor() as cur:
            cur.execute(
                """INSERT INTO fotografias
                   (id_usuario, objeto, nombre_archivo, tipo_mime, tamano_bytes, hash_sha256, descripcion)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (hash_sha256) WHERE hash_sha256 IS NOT NULL DO NOTHING
                   RETURNING id_foto""",
                (usuarios[indice % len(usuarios)], contenido, ruta.name, mime, len(contenido), digest,
                 ruta.stem.replace("_", " ")),
            )
            insertadas += int(cur.fetchone() is not None)
            omitidas += int(cur.rowcount == 0)
        print(f"Imagen {indice + 1}/{len(archivos)}: {ruta.name} ({len(contenido) / 1024:.1f} KB)", flush=True)

    print(f"Importación terminada: {insertadas} insertadas, {omitidas} duplicadas, {demasiado_grandes} mayores de 25 MB")


if __name__ == "__main__":
    try:
        importar()
    finally:
        close_pool()
