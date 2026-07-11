"""Verifica requisitos locales sin modificar la base de datos."""

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
IMAGES_DIR = ROOT / "imagenes"


def ok(mensaje: str) -> None:
    print(f"[OK] {mensaje}")


def error(mensaje: str) -> None:
    print(f"[ERROR] {mensaje}")


def main() -> int:
    fallos = 0
    if sys.version_info >= (3, 12):
        ok(f"Python {sys.version.split()[0]}")
    else:
        error("Se requiere Python 3.12 o superior")
        fallos += 1

    if not ENV_FILE.exists():
        error("Falta .env; copia .env.example y completa las credenciales")
        return 1
    load_dotenv(ENV_FILE)
    ok("Archivo .env encontrado")

    requeridas = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    faltantes = [nombre for nombre in requeridas if not os.getenv(nombre)]
    if faltantes:
        error("Variables vacías en .env: " + ", ".join(faltantes))
        fallos += 1
    else:
        ok("Variables de PostgreSQL completas")

    imagenes = []
    if IMAGES_DIR.exists():
        imagenes = [p for p in IMAGES_DIR.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
    if imagenes:
        ok(f"Carpeta imagenes: {len(imagenes)} archivos compatibles")
    else:
        print("[AVISO] No hay imágenes locales; el resto del poblado sí puede ejecutarse")

    if not faltantes:
        conninfo = (
            f"host={os.getenv('DB_HOST')} port={os.getenv('DB_PORT')} "
            f"dbname={os.getenv('DB_NAME')} user={os.getenv('DB_USER')} "
            f"password={os.getenv('DB_PASSWORD')} connect_timeout=5"
        )
        try:
            with psycopg.connect(conninfo) as conn:
                version = conn.execute("SHOW server_version").fetchone()[0]
                tabla = conn.execute("SELECT to_regclass('public.usuarios')").fetchone()[0]
            ok(f"Conexión PostgreSQL {version}")
            if tabla:
                ok("Esquema AcademiNet inicializado")
            else:
                print("[AVISO] Base accesible pero sin tablas; usa 'Inicializar BD'")
        except Exception as exc:
            error(f"No se pudo conectar a la base configurada: {exc}")
            fallos += 1

    print("\nConfiguración lista." if not fallos else f"\nSe encontraron {fallos} problema(s).")
    return 0 if not fallos else 1


if __name__ == "__main__":
    raise SystemExit(main())
