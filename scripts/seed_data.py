"""
seed_data.py — Generación masiva de datos para AcademiNet
Genera: 10,000 usuarios + 10,000 cuentas + 100,000 publicaciones
        + fotografías + comentarios + likes

Ejecución directa:  python scripts/seed_data.py
También invocado desde el botón "Poblar" en el panel Admin.
"""

import os, sys, random, time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psycopg
from dotenv import load_dotenv

load_dotenv()

_conninfo = (
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'academinet')} "
    f"user={os.getenv('DB_USER', 'postgres')} "
    f"password={os.getenv('DB_PASSWORD', '')}"
)

TOTAL_USUARIOS      = 10_000
TOTAL_PUBLICACIONES = 100_000
BATCH_SIZE          = 500

NOMBRES = [
    "Carlos","María","José","Ana","Luis","Isabel","Juan","Sofía","Pedro","Elena",
    "Miguel","Carmen","Rafael","Laura","Antonio","Rosa","David","Patricia","Jorge","Marta",
    "Alejandro","Sandra","Roberto","Cristina","Andrés","Valeria","Francisco","Mónica","Pablo","Lucía",
    "Sebastián","Verónica","Nicolás","Gabriela","Diego","Natalia","Felipe","Camila","Ricardo","Daniela",
    "Gonzalo","Andrea","Javier","Beatriz","Martín","Teresa","Sergio","Paula","Alberto","Claudia",
]
APELLIDOS = [
    "García","Rodríguez","López","Martínez","González","Pérez","Sánchez","Ramírez","Torres","Flores",
    "Rivera","Gómez","Díaz","Reyes","Morales","Jiménez","Romero","Álvarez","Cruz","Herrera",
    "Medina","Castro","Vargas","Ortiz","Ramos","Delgado","Suárez","Vega","Mendoza","Guerrero",
    "Quispe","Morocho","Loja","Calle","Ponce","Tapia","Salgado","Cabrera","Naranjo","Aguirre",
]
DOMINIOS   = ["ucuenca.edu.ec","investigacion.ec","academia.edu","univ.ec"]
TIPOS_PUB  = ["paper","microblog","comentario"]
CARGOS     = ["profesor","investigador"]

TITULOS_PAPER = [
    "Análisis de redes neuronales aplicadas a imágenes satelitales",
    "Impacto del cambio climático en ecosistemas andinos",
    "Optimización de algoritmos genéticos para scheduling",
    "Seguridad en sistemas distribuidos: un enfoque formal",
    "Machine Learning para predicción de abandono estudiantil",
    "Blockchain aplicado a registros académicos descentralizados",
    "Métodos numéricos para ecuaciones diferenciales parciales",
    "Bioinformática: análisis de secuencias genómicas en R",
    "Computación cuántica: estado del arte y perspectivas",
    "Modelos de simulación para tráfico vehicular urbano",
]
TITULOS_MICRO = [
    "Reflexiones sobre la educación universitaria hoy",
    "Nuevas herramientas para investigación colaborativa",
    "La IA en el aula: oportunidades y desafíos",
    "Publicando desde el laboratorio de datos",
    "Avances en el proyecto de investigación #3",
    "Convocatoria a colaboradores para paper en revisión",
    "Compartiendo resultados preliminares del experimento",
    "¿Cuál es el futuro de la investigación abierta?",
]
CONTENIDOS = [
    "Este trabajo presenta una revisión sistemática de la literatura existente.",
    "Los resultados obtenidos demuestran una mejora significativa del 34%.",
    "Metodología basada en el paradigma cuantitativo con enfoque experimental.",
    "Se utilizaron técnicas de procesamiento de lenguaje natural (NLP).",
    "La validación se realizó con un dataset de 50,000 muestras etiquetadas.",
    "Trabajo en progreso, abierto a colaboraciones y revisiones.",
    "Agradezco a la Universidad de Cuenca por el financiamiento de esta investigación.",
    None,
]


def generar_cedula_unica(existentes: set) -> str:
    while True:
        c = "".join([str(random.randint(0, 9)) for _ in range(10)])
        if c not in existentes:
            existentes.add(c)
            return c


def rand_fecha(dias_atras=365) -> datetime:
    return datetime.now() - timedelta(
        days=random.randint(0, dias_atras),
        hours=random.randint(0, 23)
    )


def batch_insert(cur, sql: str, data: list):
    """Inserta en lotes usando executemany (psycopg v3)."""
    cur.executemany(sql, data)


def seed(forzar: bool = False):
    print("Conectando a PostgreSQL...")
    conn = psycopg.connect(_conninfo)

    # ── Guarda: evitar poblar si ya hay datos suficientes ─────
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM usuarios")
        n_usuarios = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM publicaciones")
        n_pubs = cur.fetchone()[0]

    if not forzar and n_usuarios >= TOTAL_USUARIOS and n_pubs >= TOTAL_PUBLICACIONES:
        print(f"⚠️  La BD ya tiene {n_usuarios} usuarios y {n_pubs} publicaciones.")
        print("   Usa forzar=True (o el botón 'Forzar repoblación') para agregar más.")
        conn.close()
        return

    print(f"Estado actual: {n_usuarios} usuarios, {n_pubs} publicaciones")

    # ── 1. Usuarios ───────────────────────────────────────────
    print(f"Insertando {TOTAL_USUARIOS} usuarios...")
    cedulas = set()
    with conn.cursor() as cur:
        cur.execute("SELECT cedula FROM usuarios")
        for row in cur.fetchall():
            cedulas.add(row[0])

    usuarios_batch = []
    for i in range(TOTAL_USUARIOS):
        cedula   = generar_cedula_unica(cedulas)
        nombres  = random.choice(NOMBRES)
        apellido = random.choice(APELLIDOS) + " " + random.choice(APELLIDOS)
        cargo    = random.choice(CARGOS)
        dominio  = random.choice(DOMINIOS)
        email    = f"{nombres.lower()}.{i}@{dominio}"
        usuarios_batch.append((cedula, apellido, nombres, cargo, email))

        if len(usuarios_batch) == BATCH_SIZE:
            with conn.cursor() as cur:
                batch_insert(
                    cur,
                    "INSERT INTO usuarios (cedula,apellidos,nombres,cargo,email) "
                    "VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    usuarios_batch
                )
            conn.commit()
            usuarios_batch = []
            print(f"  Usuarios insertados: {i+1}/{TOTAL_USUARIOS}", end="\r")

    if usuarios_batch:
        with conn.cursor() as cur:
            batch_insert(
                cur,
                "INSERT INTO usuarios (cedula,apellidos,nombres,cargo,email) "
                "VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                usuarios_batch
            )
        conn.commit()
    print(f"\n  ✅ Usuarios completados")

    # ── 2. Cuentas ────────────────────────────────────────────
    print("Creando cuentas para usuarios sin cuenta...")
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO cuentas (id_usuario, tipo, privacidad)
            SELECT u.id_usuario,
                   CASE WHEN random() > 0.8 THEN 'premium' ELSE 'regular' END,
                   CASE WHEN random() > 0.7 THEN 'privado' ELSE 'publico' END
            FROM usuarios u
            WHERE NOT EXISTS (SELECT 1 FROM cuentas c WHERE c.id_usuario = u.id_usuario)
        """)
    conn.commit()
    print("  ✅ Cuentas completadas")

    # ── 3. IDs de usuarios disponibles ───────────────────────
    with conn.cursor() as cur:
        cur.execute("SELECT id_usuario FROM usuarios ORDER BY id_usuario")
        ids_usuarios = [r[0] for r in cur.fetchall()]
    print(f"  Total usuarios en BD: {len(ids_usuarios)}")

    # ── 4. Publicaciones ──────────────────────────────────────
    print(f"Insertando {TOTAL_PUBLICACIONES} publicaciones...")
    pub_batch = []
    for i in range(TOTAL_PUBLICACIONES):
        tipo  = random.choice(TIPOS_PUB)
        autor = random.choice(ids_usuarios)
        fecha = rand_fecha(730)
        titulo = (
            random.choice(TITULOS_PAPER) + f" [{random.randint(2020,2025)}]"
            if tipo == "paper"
            else random.choice(TITULOS_MICRO)
        )
        contenido = random.choice(CONTENIDOS)
        pub_batch.append((titulo, tipo, autor, fecha, contenido))

        if len(pub_batch) == BATCH_SIZE:
            with conn.cursor() as cur:
                batch_insert(
                    cur,
                    "INSERT INTO publicaciones (titulo,tipo,autor,fecha_publicacion,contenido) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    pub_batch
                )
            conn.commit()
            pub_batch = []
            print(f"  Publicaciones insertadas: {i+1}/{TOTAL_PUBLICACIONES}", end="\r")

    if pub_batch:
        with conn.cursor() as cur:
            batch_insert(
                cur,
                "INSERT INTO publicaciones (titulo,tipo,autor,fecha_publicacion,contenido) "
                "VALUES (%s,%s,%s,%s,%s)",
                pub_batch
            )
        conn.commit()
    print(f"\n  ✅ Publicaciones completadas")

    # ── 5. Seguidores ─────────────────────────────────────────
    print("Generando relaciones de seguidores...")
    seg_batch = set()
    sample = random.sample(ids_usuarios, min(500, len(ids_usuarios)))
    for uid in sample:
        for _ in range(random.randint(1, 10)):
            followed = random.choice(ids_usuarios)
            if followed != uid:
                seg_batch.add((uid, followed))
    with conn.cursor() as cur:
        batch_insert(
            cur,
            "INSERT INTO seguidores (id_seguidor, id_seguido) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            list(seg_batch)
        )
    conn.commit()
    print(f"  ✅ {len(seg_batch)} relaciones de seguidores")

    # ── 6. Likes en publicaciones ─────────────────────────────
    print("Generando likes...")
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM publicaciones ORDER BY RANDOM() LIMIT 1000")
        pub_ids = [r[0] for r in cur.fetchall()]
    likes_batch = set()
    for pid in pub_ids:
        for _ in range(random.randint(0, 15)):
            uid = random.choice(ids_usuarios)
            likes_batch.add((pid, uid))
    with conn.cursor() as cur:
        batch_insert(
            cur,
            "INSERT INTO likes_publicaciones (id_publicacion, id_usuario) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            list(likes_batch)
        )
    conn.commit()
    print(f"  ✅ {len(likes_batch)} likes generados")

    # ── 7. Comentarios ────────────────────────────────────────
    print("Generando comentarios...")
    frases = [
        "Excelente investigación.", "Muy interesante, gracias por compartir.",
        "¿Podrías ampliar sobre la metodología?", "Me parece un aporte valioso.",
        "Pendiente revisar las referencias.", "Comparto esta publicación con mis estudiantes.",
        "Trabajo muy bien documentado.", "¿Hay datos complementarios disponibles?",
    ]
    com_batch = []
    for pid in random.sample(pub_ids, min(200, len(pub_ids))):
        for _ in range(random.randint(0, 8)):
            uid = random.choice(ids_usuarios)
            com_batch.append((pid, uid, random.choice(frases), rand_fecha(60)))
    if com_batch:
        with conn.cursor() as cur:
            batch_insert(
                cur,
                "INSERT INTO comentarios (id_publicacion, id_usuario, contenido, fecha_comentario) "
                "VALUES (%s,%s,%s,%s)",
                com_batch
            )
        conn.commit()
    print(f"  ✅ {len(com_batch)} comentarios generados")

    conn.close()
    print("\n🎉 Población masiva completada exitosamente.")


if __name__ == "__main__":
    t0 = time.time()
    forzar = os.getenv("SEED_FORZAR", "0") == "1"
    seed(forzar=forzar)
    print(f"⏱️  Tiempo total: {time.time() - t0:.1f}s")
