"""
concurrency_test.py — Prueba de control de concurrencia
Simula 50 usuarios intentando comentar simultáneamente en la misma publicación.

Justificación de aislamiento:
- READ COMMITTED (por defecto en PostgreSQL): cada sentencia ve datos confirmados.
- SELECT FOR UPDATE en publicaciones bloquea la fila durante la transacción,
  evitando lecturas sucias ni actualizaciones perdidas.
- Cambiar ISOLATION_LEVEL a "SERIALIZABLE" para detectar anomalías write-skew.

Ejecución: python scripts/concurrency_test.py
"""

import os, sys, random, time, threading
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psycopg
from psycopg import IsolationLevel
from dotenv import load_dotenv

load_dotenv()

_conninfo = (
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'academinet')} "
    f"user={os.getenv('DB_USER', 'postgres')} "
    f"password={os.getenv('DB_PASSWORD', '')}"
)

NUM_THREADS     = 50
ISOLATION_LEVEL = IsolationLevel.READ_COMMITTED   # o SERIALIZABLE para comparar

resultados = {
    "exitosos": 0,
    "fallidos":  0,
    "tiempos":   [],
    "errores":   [],
}
lock = threading.Lock()


def obtener_publicacion_objetivo() -> int | None:
    with psycopg.connect(_conninfo) as conn:
        id_solicitado = os.getenv("CONCURRENCY_PUBLICATION_ID")
        if id_solicitado:
            row = conn.execute(
                "SELECT id FROM publicaciones WHERE id = %s AND estado = 'activo'",
                (int(id_solicitado),),
            ).fetchone()
            if not row:
                raise ValueError(f"La publicación #{id_solicitado} no existe o no está activa")
            return row[0]

        row = conn.execute("""
            SELECT id_publicacion, COUNT(*) as cnt
            FROM comentarios
            GROUP BY id_publicacion
            ORDER BY cnt DESC
            LIMIT 1
        """).fetchone()
        if not row:
            row2 = conn.execute(
                "SELECT id FROM publicaciones WHERE estado='activo' LIMIT 1"
            ).fetchone()
            return row2[0] if row2 else None
        return row[0]


def obtener_usuarios_muestra(n: int) -> list:
    with psycopg.connect(_conninfo) as conn:
        rows = conn.execute(
            f"SELECT id_usuario FROM usuarios ORDER BY RANDOM() LIMIT {n}"
        ).fetchall()
    return [r[0] for r in rows]


def worker_comentar(thread_id: int, id_usuario: int, id_publicacion: int):
    t0 = time.time()
    try:
        with psycopg.connect(_conninfo) as conn:
            conn.isolation_level = ISOLATION_LEVEL

            # SELECT FOR UPDATE: bloquea la fila mientras se inserta el comentario
            row = conn.execute(
                "SELECT id FROM publicaciones WHERE id = %s AND estado = 'activo' FOR UPDATE",
                (id_publicacion,)
            ).fetchone()

            if not row:
                raise Exception("Publicación no disponible")

            contenido = (
                f"Comentario concurrente del usuario #{id_usuario} "
                f"— hilo {thread_id} [{datetime.now().isoformat()}]"
            )
            conn.execute(
                "INSERT INTO comentarios (id_publicacion, id_usuario, contenido) VALUES (%s, %s, %s)",
                (id_publicacion, id_usuario, contenido)
            )
            conn.commit()

        elapsed = time.time() - t0
        with lock:
            resultados["exitosos"] += 1
            resultados["tiempos"].append(elapsed)
            completadas = resultados["exitosos"] + resultados["fallidos"]
            print(f"Progreso: {completadas}/{NUM_THREADS} transacciones completadas", flush=True)

    except Exception as e:
        with lock:
            resultados["fallidos"] += 1
            resultados["errores"].append(str(e))
            completadas = resultados["exitosos"] + resultados["fallidos"]
            print(f"Progreso: {completadas}/{NUM_THREADS} transacciones completadas", flush=True)


def run_concurrency_test():
    print("=" * 60)
    print("AcademiNet — Prueba de Concurrencia")
    print(f"Threads:           {NUM_THREADS}")
    print(f"Nivel aislamiento: {ISOLATION_LEVEL.name}")
    print("=" * 60)

    pub_id = obtener_publicacion_objetivo()
    if not pub_id:
        print("❌ No hay publicaciones activas. Pobla la BD primero.")
        return

    usuarios = obtener_usuarios_muestra(NUM_THREADS)
    if len(usuarios) < NUM_THREADS:
        usuarios = (usuarios * (NUM_THREADS // len(usuarios) + 1))[:NUM_THREADS]

    print(f"Publicación objetivo: #{pub_id}")
    print(f"Disparando {NUM_THREADS} hilos simultáneos...\n")

    t_inicio = time.time()
    hilos = [
        threading.Thread(target=worker_comentar, args=(i, usuarios[i], pub_id))
        for i in range(NUM_THREADS)
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    t_total = time.time() - t_inicio
    tiempos = resultados["tiempos"]

    print("=" * 60)
    print("RESULTADOS")
    print("=" * 60)
    print(f"✅ Transacciones exitosas:  {resultados['exitosos']}/{NUM_THREADS}")
    print(f"❌ Transacciones fallidas:  {resultados['fallidos']}/{NUM_THREADS}")
    print(f"⏱️  Tiempo total:            {t_total:.3f}s")
    if tiempos:
        avg = sum(tiempos) / len(tiempos)
        print(f"⏱️  Tiempo promedio/tx:      {avg*1000:.1f}ms")
        print(f"⏱️  Tiempo máximo:           {max(tiempos)*1000:.1f}ms")
        print(f"⏱️  Tiempo mínimo:           {min(tiempos)*1000:.1f}ms")

    if resultados["errores"]:
        print("\nErrores registrados:")
        for e in set(resultados["errores"]):
            print(f"  - {e}")

    with psycopg.connect(_conninfo) as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM comentarios WHERE id_publicacion = %s", (pub_id,)
        ).fetchone()[0]

    print(f"\n📊 Total comentarios en publicación #{pub_id}: {total}")
    print("=" * 60)
    print(f"\nJustificación:")
    print(f"  Nivel '{ISOLATION_LEVEL.name}' + SELECT FOR UPDATE garantiza que")
    print(f"  no ocurran lecturas sucias ni actualizaciones perdidas.")


if __name__ == "__main__":
    run_concurrency_test()
