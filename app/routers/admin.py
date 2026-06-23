from fastapi import APIRouter, BackgroundTasks
from app.database import get_cursor, init_db
from app.models.schemas import Respuesta
import subprocess, sys, os

router = APIRouter(prefix="/admin", tags=["Administración"])


@router.post("/init-db", response_model=Respuesta)
def inicializar_base():
    """Ejecuta todos los scripts SQL (schema, procedimientos, triggers, índices)."""
    try:
        scripts = init_db()
        return Respuesta(
            success=True,
            mensaje=f"Base de datos inicializada. Scripts ejecutados: {scripts}"
        )
    except Exception as e:
        return Respuesta(success=False, mensaje=str(e))


@router.post("/poblar", response_model=Respuesta)
def poblar_base(background_tasks: BackgroundTasks, forzar: bool = False):
    """
    Dispara el script de generación masiva de datos en segundo plano.
    forzar=false (default): omite si la BD ya tiene 10K usuarios y 100K publicaciones.
    forzar=true: agrega otro lote aunque ya haya datos.
    """
    def _run(forzar_flag: bool):
        script = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "seed_data.py")
        env = os.environ.copy()
        env["SEED_FORZAR"] = "1" if forzar_flag else "0"
        subprocess.run([sys.executable, script], check=True, env=env)

    background_tasks.add_task(_run, forzar)
    accion = "forzada" if forzar else "protegida (se omite si ya hay datos suficientes)"
    return Respuesta(
        success=True,
        mensaje=f"Población masiva iniciada [{accion}]. Puede tomar varios minutos."
    )


@router.get("/estadisticas")
def estadisticas():
    with get_cursor() as cur:
        cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM usuarios)       AS total_usuarios,
                (SELECT COUNT(*) FROM cuentas)        AS total_cuentas,
                (SELECT COUNT(*) FROM publicaciones WHERE estado='activo') AS total_publicaciones,
                (SELECT COUNT(*) FROM fotografias)    AS total_fotografias,
                (SELECT COUNT(*) FROM comentarios)    AS total_comentarios,
                (SELECT COUNT(*) FROM likes_publicaciones) AS total_likes,
                (SELECT COUNT(*) FROM auditoria)      AS total_auditorias
        """)
        return cur.fetchone()


@router.get("/auditoria")
def log_auditoria(limit: int = 50, offset: int = 0):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM auditoria ORDER BY fecha_evento DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return cur.fetchall()


@router.post("/concurrencia", response_model=Respuesta)
def test_concurrencia(background_tasks: BackgroundTasks):
    """Lanza el script de prueba de concurrencia (50 usuarios simultáneos)."""
    def _run():
        script = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "concurrency_test.py")
        subprocess.run([sys.executable, script], check=True)

    background_tasks.add_task(_run)
    return Respuesta(
        success=True,
        mensaje="Prueba de concurrencia iniciada (50 usuarios simultáneos)."
    )
