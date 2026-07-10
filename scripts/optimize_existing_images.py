"""Optimiza de forma reanudable las fotografías existentes sin miniatura."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import close_pool, get_cursor, init_db
from app.image_processing import optimizar_imagen


def ejecutar() -> None:
    init_db()
    procesadas = errores = 0
    while True:
        with get_cursor() as cur:
            cur.execute("SELECT id_foto, objeto FROM fotografias WHERE objeto IS NOT NULL AND miniatura IS NULL ORDER BY id_foto LIMIT 10")
            filas = cur.fetchall()
        if not filas:
            break
        for fila in filas:
            try:
                imagen = optimizar_imagen(bytes(fila["objeto"]))
                with get_cursor() as cur:
                    cur.execute(
                        """UPDATE fotografias SET objeto=%s, miniatura=%s, tipo_mime='image/webp',
                           tipo_mime_miniatura='image/webp', tamano_bytes=%s WHERE id_foto=%s""",
                        (imagen.objeto, imagen.miniatura, len(imagen.objeto), fila["id_foto"]),
                    )
                procesadas += 1
            except Exception as exc:
                errores += 1
                print(f"Foto #{fila['id_foto']} omitida: {exc}")
                # Evita un ciclo infinito con archivos dañados.
                with get_cursor() as cur:
                    cur.execute("UPDATE fotografias SET miniatura = ''::bytea WHERE id_foto = %s", (fila["id_foto"],))
        print(f"Optimizadas: {procesadas}; errores: {errores}")
    print(f"Proceso terminado: {procesadas} optimizadas, {errores} errores")


if __name__ == "__main__":
    try:
        ejecutar()
    finally:
        close_pool()
