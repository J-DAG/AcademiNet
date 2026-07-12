"""Compara A/B/C sin y con índices estratégicos y siempre los restaura."""

import json
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg
from dotenv import load_dotenv

from app.routers.admin import _CONSULTAS_EXPLAIN

ROOT = Path(__file__).resolve().parents[1]
INDEX_SQL = ROOT / "database" / "04_indexes.sql"
RUNS = 3

INDEXES = [
    "idx_pub_autor", "idx_pub_fecha", "idx_pub_autor_estado", "idx_pub_tipo",
    "idx_pub_id_foto", "idx_com_publicacion", "idx_com_pub_fecha",
    "idx_com_usuario", "idx_foto_usuario", "idx_likes_pub_pub",
    "idx_likes_pub_usr", "idx_usr_cargo", "idx_usr_email", "idx_tc_origen",
    "idx_tc_destino",
]

TABLES = [
    "usuarios", "publicaciones", "fotografias", "comentarios",
    "likes_publicaciones", "transferencias_creditos",
]


def analizar(conn) -> None:
    for table in TABLES:
        conn.execute(f"ANALYZE {table}")
    conn.commit()


def resumen_plan(documento: dict) -> dict:
    plan = documento["Plan"]
    indices, nodes = [], []

    def walk(node: dict) -> None:
        if node.get("Node Type") and node["Node Type"] not in nodes:
            nodes.append(node["Node Type"])
        if node.get("Index Name") and node["Index Name"] not in indices:
            indices.append(node["Index Name"])
        for child in node.get("Plans", []):
            walk(child)

    walk(plan)
    return {
        "startup_cost": plan["Startup Cost"],
        "total_cost": plan["Total Cost"],
        "planning_ms": documento["Planning Time"],
        "execution_ms": documento["Execution Time"],
        "rows": plan["Actual Rows"],
        "buffers_hit": plan.get("Shared Hit Blocks", 0),
        "buffers_read": plan.get("Shared Read Blocks", 0),
        "main_node": plan["Node Type"],
        "indices": indices,
        "nodes": nodes,
    }


def medir(conn) -> dict:
    resultado = {}
    for key, query in _CONSULTAS_EXPLAIN.items():
        runs = []
        for _ in range(RUNS):
            document = conn.execute(
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query
            ).fetchone()[0][0]
            runs.append(resumen_plan(document))
        representative = min(runs, key=lambda r: abs(r["execution_ms"] - statistics.median(x["execution_ms"] for x in runs)))
        representative["execution_runs_ms"] = [round(r["execution_ms"], 3) for r in runs]
        representative["execution_median_ms"] = round(statistics.median(r["execution_ms"] for r in runs), 3)
        resultado[key] = representative
    return resultado


def main() -> int:
    load_dotenv(ROOT / ".env")
    conninfo = (
        f"host={os.getenv('DB_HOST', 'localhost')} port={os.getenv('DB_PORT', '5432')} "
        f"dbname={os.getenv('DB_NAME', 'academinet')} user={os.getenv('DB_USER', 'postgres')} "
        f"password={os.getenv('DB_PASSWORD', '')}"
    )
    result = {}
    with psycopg.connect(conninfo) as conn:
        # Aísla el efecto de los índices y evita variación por arranque de workers.
        conn.execute("SET max_parallel_workers_per_gather = 0")
        try:
            for index in INDEXES:
                conn.execute(f"DROP INDEX IF EXISTS {index}")
            conn.commit()
            analizar(conn)
            result["sin_indices"] = medir(conn)
        finally:
            conn.execute(INDEX_SQL.read_text(encoding="utf-8"))
            conn.commit()
            analizar(conn)
        result["con_indices"] = medir(conn)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
