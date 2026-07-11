from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from app.database import get_cursor, init_db
from app.models.schemas import Respuesta
import subprocess, sys, os
import threading
import time

router = APIRouter(prefix="/admin", tags=["Administración"])

_concurrencia_lock = threading.Lock()
_concurrencia_estado = {
    "estado": "inactivo", "inicio": None, "fin": None,
    "salida": [], "error": None,
}
_poblacion_lock = threading.Lock()
_poblacion_en_curso = False

_CONSULTAS_EXPLAIN = {
    "A": """
        SELECT u.id_usuario, u.nombres, u.apellidos, u.cargo, COUNT(p.id) AS total_pubs
        FROM usuarios u
        JOIN publicaciones p ON p.autor=u.id_usuario AND p.estado='activo'
        GROUP BY u.id_usuario, u.nombres, u.apellidos, u.cargo
        HAVING COUNT(p.id)>10 ORDER BY total_pubs DESC
    """,
    "B": """
        SELECT u.id_usuario, u.nombres, u.apellidos,
               COUNT(DISTINCT p.id_foto) AS total_fotos,
               COUNT(DISTINCT c.id_comentario) AS total_comentarios
        FROM usuarios u
        JOIN publicaciones p ON p.autor=u.id_usuario AND p.estado='activo' AND p.id_foto IS NOT NULL
        JOIN comentarios c ON c.id_publicacion=p.id AND c.fecha_comentario >= NOW()-INTERVAL '1 month'
        GROUP BY u.id_usuario, u.nombres, u.apellidos
        HAVING COUNT(DISTINCT c.id_comentario)>50
        ORDER BY total_fotos DESC LIMIT 10
    """,
    "C": """
        SELECT p.id, p.titulo, (u.nombres||' '||u.apellidos) AS autor, f.id_foto,
               COUNT(DISTINCT lp.id_like)+COUNT(DISTINCT c.id_comentario) AS total_interacciones
        FROM publicaciones p
        JOIN fotografias f ON f.id_foto=p.id_foto
        JOIN usuarios u ON u.id_usuario=p.autor
        LEFT JOIN likes_publicaciones lp ON lp.id_publicacion=p.id
        LEFT JOIN comentarios c ON c.id_publicacion=p.id
        WHERE p.estado='activo'
        GROUP BY p.id, p.titulo, u.nombres, u.apellidos, f.id_foto
        ORDER BY total_interacciones DESC LIMIT 20
    """,
}


def _resumir_plan(nodo: dict) -> tuple[list[str], list[str]]:
    nodos, indices = [], []
    def recorrer(actual: dict):
        tipo = actual.get("Node Type")
        if tipo and tipo not in nodos:
            nodos.append(tipo)
        indice = actual.get("Index Name")
        if indice and indice not in indices:
            indices.append(indice)
        for hijo in actual.get("Plans", []):
            recorrer(hijo)
    recorrer(nodo)
    return nodos, indices


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
    global _poblacion_en_curso
    with _poblacion_lock:
        if _poblacion_en_curso:
            return Respuesta(success=False, mensaje="Ya existe una población masiva en ejecución.")
        _poblacion_en_curso = True

    # El botón es autosuficiente: garantiza primero que esquema, funciones,
    # triggers e índices estén instalados.
    try:
        init_db()
    except Exception:
        with _poblacion_lock:
            _poblacion_en_curso = False
        raise

    def _run(forzar_flag: bool):
        global _poblacion_en_curso
        script = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "seed_data.py")
        env = os.environ.copy()
        env["SEED_FORZAR"] = "1" if forzar_flag else "0"
        try:
            subprocess.run([sys.executable, script], check=True, env=env)
        finally:
            with _poblacion_lock:
                _poblacion_en_curso = False

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
def log_auditoria(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM auditoria ORDER BY fecha_evento DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return cur.fetchall()


@router.get("/optimizacion/{consulta}")
def analizar_optimizacion(consulta: str):
    clave = consulta.upper()
    sql = _CONSULTAS_EXPLAIN.get(clave)
    if not sql:
        raise HTTPException(status_code=404, detail="Consulta de optimización inválida")
    with get_cursor() as cur:
        cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql)
        documento = cur.fetchone()["QUERY PLAN"][0]
    plan = documento["Plan"]
    nodos, indices = _resumir_plan(plan)
    return {
        "consulta": clave,
        "costo_inicial": plan.get("Startup Cost"),
        "costo_final": plan.get("Total Cost"),
        "filas_estimadas": plan.get("Plan Rows"),
        "filas_reales": plan.get("Actual Rows"),
        "planning_time_ms": documento.get("Planning Time"),
        "execution_time_ms": documento.get("Execution Time"),
        "buffers_hit": plan.get("Shared Hit Blocks", 0),
        "buffers_read": plan.get("Shared Read Blocks", 0),
        "nodo_principal": plan.get("Node Type"),
        "nodos": nodos,
        "indices": indices,
    }


@router.delete("/publicaciones/{id_publicacion}", response_model=Respuesta)
def eliminar_publicacion_admin(id_publicacion: int):
    """Borrado lógico administrativo; obtiene el autor desde PostgreSQL."""
    with get_cursor() as cur:
        cur.execute("SELECT autor FROM publicaciones WHERE id = %s", (id_publicacion,))
        publicacion = cur.fetchone()
        if not publicacion:
            raise HTTPException(status_code=404, detail="Publicación no encontrada")
        cur.execute(
            "SELECT eliminar_publicacion(%s, %s) AS resultado",
            (id_publicacion, publicacion["autor"]),
        )
        resultado = cur.fetchone()["resultado"]
    if not resultado["success"]:
        raise HTTPException(status_code=400, detail=resultado["mensaje"])
    return Respuesta(success=True, mensaje=resultado["mensaje"])


@router.post("/concurrencia", response_model=Respuesta)
def test_concurrencia(background_tasks: BackgroundTasks, id_publicacion: int | None = Query(None, gt=0)):
    """Lanza una única prueba y conserva su salida para monitorización."""
    with _concurrencia_lock:
        if _concurrencia_estado["estado"] == "ejecutando":
            return Respuesta(success=False, mensaje="Ya existe una prueba de concurrencia en ejecución.")
        _concurrencia_estado.update(
            estado="ejecutando", inicio=time.time(), fin=None, salida=[], error=None
        )

    def _run():
        script = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "concurrency_test.py")
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        if id_publicacion is not None:
            env["CONCURRENCY_PUBLICATION_ID"] = str(id_publicacion)
        try:
            proceso = subprocess.Popen(
                [sys.executable, "-u", script], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                errors="replace", env=env,
            )
            assert proceso.stdout is not None
            for linea in proceso.stdout:
                # Replica la salida del proceso en la terminal de Uvicorn y,
                # al mismo tiempo, la conserva para el monitor del frontend.
                print(linea, end="", flush=True)
                with _concurrencia_lock:
                    _concurrencia_estado["salida"].append(linea.rstrip())
                    _concurrencia_estado["salida"] = _concurrencia_estado["salida"][-200:]
            codigo = proceso.wait()
            with _concurrencia_lock:
                _concurrencia_estado["estado"] = "completado" if codigo == 0 else "error"
                _concurrencia_estado["error"] = None if codigo == 0 else f"El proceso terminó con código {codigo}"
                _concurrencia_estado["fin"] = time.time()
        except Exception as exc:
            with _concurrencia_lock:
                _concurrencia_estado.update(estado="error", error=str(exc), fin=time.time())

    background_tasks.add_task(_run)
    return Respuesta(
        success=True,
        mensaje=(f"Prueba iniciada sobre la publicación #{id_publicacion}."
                 if id_publicacion else "Prueba iniciada sobre una publicación seleccionada automáticamente.")
    )


@router.get("/concurrencia/estado")
def estado_concurrencia():
    with _concurrencia_lock:
        estado = dict(_concurrencia_estado)
        estado["salida"] = list(_concurrencia_estado["salida"])
    ahora = estado["fin"] or time.time()
    estado["duracion_segundos"] = round(ahora - estado["inicio"], 2) if estado["inicio"] else 0
    return estado
