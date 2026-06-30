# Proyecto: "AcademiNet: Motor de Datos de Alta Concurrencia para una Red Social Universitaria"

**Universidad:** Universidad de Cuenca  
**Asignatura:** Base de Datos II  
**Trabajo:** Trabajo Final  
**Profesor:** José Ochoa Brito  

---

## 📝 Descripción del Proyecto
El objetivo es desarrollar el backend (capa de datos) y una pequeña aplicación/API de interfaz para una red social académica. Se puede utilizar el software o lenguaje de programación de su preferencia, conectado a un sistema de gestión de bases de datos entre **PostgreSQL** u **Oracle 26ai**.

El sistema permitirá:
* Registrar **Usuarios** (profesores o investigadores).
* Gestionar **Cuentas**.
* Registrar **Publicaciones** (papers, microblogging científico, comentarios).
* Almacenar metadatos de **Fotografías** de investigaciones o trabajo de campo.

---

## 🛠️ Requerimientos Técnicos

### Generalidades
* **Modalidad:** Trabajo grupal de 3 personas (excepcionalmente grupos de 2).
* **Atributos mínimos y Reglas de Integridad:** Incluir al menos 3 atributos por relación. Se deben aplicar las siguientes restricciones estrictas en el diseño:
  * **Usuarios:** `id_usuario`, `cedula` (**Debe ser ÚNICA para evitar duplicados e identificaciones falsas**), `apellidos`, `nombres`, `cargo` (restringido mediante un `CHECK` a solo 'profesor' o 'investigador').
  * **Cuentas:** `id_usuario`, `tipo` (regular, premium), `fecha_creacion`, `numero_seguidores` (debe ser `DEFAULT 0` y `CHECK >= 0`), `privacidad`, `estado` (activo, inactivo).
  * **Publicaciones:** `id`, `titulo`, `tipo`, `autor` (`id_usuario`), `fecha_publicacion` (no puede ser mayor a la fecha actual), `nro_citaciones` (`CHECK >= 0`).
  * **Fotografías:** `objeto` [imagen/BYTEA], `descripcion`, `nro_likes` (`CHECK >= 0`).
* **Relaciones adicionales:** Diseñar tablas intermedias para gestionar interacciones como comentarios sobre publicaciones o fotografías, garantizando la integridad referencial (`FOREIGN KEY`) con borrado o actualización en cascada según corresponda.

---

## 🚀 Módulos Obligatorios

### 1. Arranque de BD (Volumetría)
* Generación de datos falsos mediante scripts generadores.
* La aplicación debe proveer una opción (botón) para poblar la base de datos con al menos **100,000 publicaciones** y **10,000 usuarios**. 
* *Nota de diseño:* Los scripts de población masiva deben generar cédulas aleatorias únicas válidas para no violar la restricción de unicidad.

### 2. SQL Procedural y Triggers
* **Procedimientos y Funciones:** La lógica crítica de negocio debe ejecutarse mediante funciones almacenadas (PL/pgSQL en PostgreSQL o PL/SQL en Oracle).
  * *Ejemplo:* Un procedimiento `RegistrarUsuarioYCuenta(...)` que cree ambas entidades simultáneamente. **Este procedimiento debe capturar excepciones (como el intento de duplicar una cédula) y retornar un mensaje de error controlado a la aplicación.**
* **Triggers de Auditoría y Control:** Implementar disparadores para reglas de negocio complejas:
  * Registro automático en una tabla de auditoría cuando un usuario cambie su foto de perfil o elimine una publicación.
  * Mecanismo anti-spam que impida a un usuario publicar más de 5 veces en un lapso de 1 minuto.

### 3. Transacciones y Propiedades ACID
* **Sistema de "puntos/créditos de investigación":** Al dar "Me gusta" o "Cita" a una publicación, se transfiere un crédito del usuario A al usuario B.
* El flujo debe envolverse explícitamente en bloques transaccionales (`BEGIN...COMMIT / ROLLBACK`) asegurando las propiedades ACID (especialmente Atomicidad y Aislamiento).
* Se deben simular fallos a mitad de la operación para demostrar que el sistema regresa a un estado consistente.

### 4. Control de Concurrencia
* **Simulación de Eventos Masivos:** Crear un script de prueba que emule a 50 usuarios intentando interactuar (ej. comentando) de forma simultánea en la misma publicación.
* Justificar y configurar niveles de aislamiento (Read Committed, Serializable) o técnicas de bloqueo (`SELECT FOR UPDATE`) para evitar lecturas sucias o actualizaciones perdidas.

### 5. Indexación y Optimización de Consultas
Diseñar tres consultas complejas:
* **A.** Listar profesores o investigadores con más de 10 publicaciones registradas.
* **B.** Listar el top 10 de usuarios con más fotografías subidas cuyas publicaciones hayan recibido más de 50 comentarios en el último mes.
* **C.** Lista de fotografías con más interacciones.

> 📈 **Optimización:** Utilizar herramientas de diagnóstico (`EXPLAIN ANALYZE` o el plan de ejecución de Oracle) para identificar cuellos de botella. Crear índices estratégicos (B-Tree o compuestos) y demostrar cuantitativamente la reducción de costo y tiempo de respuesta.

---

## 📦 Entregables

1. **Modelo Entidad-Relación y Relacional:** Tipos de datos óptimos (ej. `BYTEA` / `BLOB` para metadatos o rutas de fotos) y mapeo de restricciones de unicidad e integridad.
2. **Scripts SQL Base:** Estructura de tablas con sus respectivas `CONSTRAINTS` (Unicidad, Checks), llaves primarias/foráneas, triggers y procedimientos.
3. **Código del Software / API:** Un pequeño programa ejecutable (Python, Node.js, Java, etc.) que sirva de puente con la base de datos.
4. **Informe de Rendimiento:** Documento con capturas de pantalla del "Antes" y "Después" de la optimización con índices, y la justificación del protocolo de control de concurrencia.

---

## ⚙️ Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Base de datos | PostgreSQL |
| Backend / API | Python 3.x + FastAPI |
| Frontend | Jinja2 templates + HTML/CSS/JS vanilla |
| Conector BD | psycopg2 (ThreadedConnectionPool) |
| Servidor | Uvicorn |

**Arranque:** `python run.py` → `http://localhost:8000`  
**Docs API:** `http://localhost:8000/docs`  
**Config:** `.env` (ya configurado) — PostgreSQL 17 en `localhost:5434`, BD `academinet`

---

## 📁 Estructura del Proyecto

```
Proyecto_BD2/
├── database/
│   ├── 01_schema.sql          ← Tablas + constraints
│   ├── 02_procedures.sql      ← Funciones PL/pgSQL
│   ├── 03_triggers.sql        ← Triggers auditoría y negocio
│   └── 04_indexes.sql         ← Índices + consultas EXPLAIN ANALYZE
├── app/
│   ├── main.py                ← Entry point FastAPI
│   ├── database.py            ← Pool de conexiones
│   ├── models/schemas.py      ← Pydantic v2
│   ├── routers/               ← users, publications, photos, accounts, admin
│   └── templates/             ← index, usuarios, publicaciones, admin
├── static/
│   ├── css/style.css
│   └── js/main.js
├── scripts/
│   ├── seed_data.py           ← Generación masiva de datos
│   └── concurrency_test.py    ← Prueba 50 usuarios simultáneos
├── run.py
├── requirements.txt
└── .env.example
```

---

## 📋 Control de Cambios

### v0.1 — 2026-06-23 — Estructura inicial del proyecto

**Archivos creados:**

#### Base de Datos (`database/`)
- `01_schema.sql` — 12 tablas: `usuarios`, `cuentas`, `publicaciones`, `fotografias`, `comentarios`, `comentarios_foto`, `likes_publicaciones`, `likes_fotografias`, `seguidores`, `citaciones`, `transferencias_creditos`, `auditoria`. Constraints requeridas: `UNIQUE(cedula)`, `CHECK(cargo IN ('profesor','investigador'))`, `DEFAULT 0 CHECK >= 0`, `CHECK(fecha_publicacion <= NOW())`.
- `02_procedures.sql` — 7 funciones PL/pgSQL:
  - `registrar_usuario_y_cuenta(...)` → crea usuario + cuenta en una sola llamada; captura `unique_violation` y `check_violation` con mensaje controlado.
  - `dar_like_publicacion(id_usuario, id_publicacion)` → registra like + transfiere 1 crédito al autor (ACID).
  - `citar_publicacion(id_usuario, pub_origen, pub_destino)` → registra citación + transfiere 2 créditos (ACID).
  - `eliminar_publicacion(id_pub, id_usuario)` → soft delete (`estado = 'eliminado'`); el trigger de auditoría lo registra.
  - `simular_fallo_creditos(origen, destino, monto, forzar_fallo)` → demuestra ROLLBACK a mitad de transferencia.
  - `consulta_profesores_activos()` → consulta A: usuarios con más de 10 publicaciones.
  - `consulta_top_fotografos()` → consulta B: top 10 fotógrafos con >50 comentarios último mes.
  - `consulta_fotos_mas_interacciones()` → consulta C: fotografías ordenadas por likes + comentarios.
- `03_triggers.sql` — 5 triggers:
  - `trg_auditoria_foto_perfil` → registra en `auditoria` cuando cambia `foto_perfil`.
  - `trg_auditoria_eliminacion` → registra el soft delete de publicaciones.
  - `trg_antispam_publicaciones` → `BEFORE INSERT`; lanza excepción si el usuario publicó ≥5 veces en el último minuto.
  - `trg_actualizar_seguidores` → `AFTER INSERT/DELETE` en `seguidores`; actualiza `numero_seguidores`.
  - `trg_actualizar_likes_foto` → `AFTER INSERT/DELETE` en `likes_fotografias`; actualiza `nro_likes`.
- `04_indexes.sql` — 14 índices B-Tree y compuestos sobre `publicaciones`, `comentarios`, `fotografias`, `likes_*`, `usuarios`, `transferencias_creditos`. Consultas A/B/C con `EXPLAIN ANALYZE` comentadas para comparar antes/después.

#### Backend (`app/`)
- `database.py` — `ThreadedConnectionPool` (2–20 conexiones), context managers `get_conn()` y `get_cursor()` con commit/rollback automático.
- `models/schemas.py` — Schemas Pydantic v2: `UsuarioCreate/Out`, `CuentaOut/Update`, `PublicacionCreate/Out`, `ComentarioCreate/Out`, `FotografiaOut`, `LikePublicacion`, `CitacionCreate`, `SimularFallo`, `SeguirUsuario`, `Respuesta`.
- `routers/users.py` — CRUD usuarios, seguir/dejar de seguir, consulta A.
- `routers/publications.py` — CRUD publicaciones, comentarios, likes (ACID), citaciones, demo ACID, consultas B y C.
- `routers/photos.py` — Subida BYTEA, listar, like y comentario en foto.
- `routers/accounts.py` — Ver/actualizar cuenta, créditos, log de auditoría.
- `routers/admin.py` — Init BD, poblar datos (background task), estadísticas globales, log auditoría, prueba concurrencia.
- `main.py` — Estáticos, templates Jinja2, routers bajo `/api`, 4 páginas HTML.

#### Frontend (`app/templates/`, `static/`)
- `base.html` — Navbar responsive, footer, toast de notificaciones.
- `index.html` — Hero, estadísticas en tiempo real, grid de 6 módulos del sistema.
- `usuarios.html` — Formulario de registro, tabla paginada con búsqueda, ver créditos, consulta A expandible.
- `publicaciones.html` — Feed paginado con filtro por tipo, nueva publicación, modal de like con crédito, acordeón de comentarios.
- `admin.html` — 6 widgets: init BD, poblar datos, prueba concurrencia, demo ACID/ROLLBACK, log auditoría, 3 consultas de optimización.
- `style.css` — Diseño responsive, navbar sticky, cards, badges, data-tables, modal, toast.
- `main.js` — `showToast()`, `toggleForm()`, `confirmAction()`.

#### Scripts (`scripts/`)
- `seed_data.py` — Batches de 500 con `execute_values`, cédulas únicas aleatorias, 10K usuarios + cuentas + 100K publicaciones + seguidores + likes + comentarios.
- `concurrency_test.py` — 50 threads simultáneos con `threading.Thread`, `SELECT FOR UPDATE`, configurable en `READ COMMITTED` / `SERIALIZABLE`. Reporta exitosos/fallidos/tiempos.

#### Raíz
- `requirements.txt` — fastapi, uvicorn, psycopg2-binary, python-dotenv, pydantic[email], jinja2, python-multipart.
- `.env.example` — Variables `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
- `run.py` — `uvicorn app.main:app --reload --port 8000`.

---

### v0.5 — 2026-06-29 — Rediseño del módulo de fotografías (URL-based)

**Motivación:** Las imágenes provienen del repositorio público `dharmx/walls` (wallpapers en GitHub). Se almacenan como URLs raw (`https://raw.githubusercontent.com/dharmx/walls/main/{path}`), no como BYTEA. Una publicación puede tener opcionalmente una foto adjunta; likes, comentarios y descripción pertenecen a la publicación, no a la foto.

**Base de datos:**
- `01_schema.sql` — Eliminadas tablas `likes_fotografias` y `comentarios_foto`. `fotografias.objeto BYTEA` → `ruta_imagen VARCHAR(500) NOT NULL`. `cuentas.foto_perfil` → VARCHAR(500). Añadida columna `id_foto INT REFERENCES fotografias(id_foto) ON DELETE SET NULL` en `publicaciones`.
- `02_procedures.sql` — Consultas B y C reescritas: B usa `p.id_foto IS NOT NULL`; C hace JOIN `publicaciones → fotografias → likes_publicaciones/comentarios` en lugar de `likes_fotografias`.
- `03_triggers.sql` — Eliminado `trg_actualizar_likes_foto` (tabla `likes_fotografias` ya no existe). Trigger de auditoría de eliminación ahora registra `id_foto`.
- `04_indexes.sql` — Eliminados índices sobre `likes_fotografias` y `comentarios_foto`. Añadido `idx_pub_id_foto ON publicaciones (id_foto) WHERE id_foto IS NOT NULL`.

**Backend:**
- `app/models/schemas.py` — `FotografiaCreate` y `FotografiaOut` usan `ruta_imagen` (sin `nro_likes`). `PublicacionCreate` añade `id_foto: Optional[int]`. `PublicacionOut` añade `id_foto` y `ruta_imagen` (joined desde fotografias).
- `app/routers/photos.py` — Eliminado endpoint de upload de archivo y de servir BYTEA. Endpoint `POST /api/fotografias/` acepta JSON con URL. Galería lista desde `/api/fotografias/`.
- `app/routers/publications.py` — Todas las queries de publicaciones hacen `LEFT JOIN fotografias f ON f.id_foto = p.id_foto` y retornan `ruta_imagen`.
- `scripts/seed_data.py` — Consulta la GitHub API (`/repos/dharmx/walls/git/trees/main?recursive=1`), filtra extensiones de imagen, inserta hasta 5 000 fotos en `fotografias` y asigna `id_foto` al ~35% de las publicaciones.

**Frontend:**
- `app/templates/fotografias.html` — Rediseñado como galería URL-based: formulario de registro por URL (con vista previa), grid de imágenes cargadas con `<img src="ruta_imagen">`, modal de imagen grande. Eliminado todo lo relacionado a BYTEA/upload/like de foto.
- `app/templates/publicaciones.html` — Tarjetas de publicación muestran miniatura `<img>` cuando `p.ruta_imagen` está presente. Formulario incluye campo "ID Foto (opcional)".
- `static/css/style.css` — Añadidos estilos `.pub-foto-wrap` y `.pub-foto-thumb` para miniaturas en publicaciones.

---

### v0.4 — 2026-06-23 — Manual de usuario y protección anti-duplicados

**Archivos nuevos/modificados:**
- `README.md` — Manual completo: requisitos, arranque, flujo del programa, descripción de cada panel (Inicio, Usuarios, Publicaciones, Admin), referencia a la API y comandos de mantenimiento.
- `scripts/seed_data.py` — Agregada guarda `forzar=False`: si la BD ya tiene ≥10K usuarios y ≥100K publicaciones, el script se detiene sin duplicar. Se activa con env var `SEED_FORZAR=1` o el parámetro `forzar=True`.
- `app/routers/admin.py` — Endpoint `POST /api/admin/poblar` acepta query param `?forzar=true/false` y lo pasa al script.
- `app/templates/admin.html` — Checkbox "Forzar repoblación" visible en el panel; desactivado por defecto.

---

### v0.3 — 2026-06-23 — Primera ejecución exitosa

**Ambiente verificado:**
- PostgreSQL 17.5 en `localhost:5434` (puerto no estándar)
- BD `academinet` creada y schema inicializado (12 tablas, 8 funciones, 5 triggers, 16 índices)
- `.env` configurado con `DB_PORT=5434`, `DB_PASSWORD=PostgreSQL`
- App corriendo en `http://localhost:8000` — todos los endpoints responden HTTP 200

**Bug corregido:** `app/routers/users.py` tenía `import psycopg2.extras` residual que impedía el arranque. Eliminado.

---

### v0.2 — 2026-06-23 — Compatibilidad con Python 3.14

**Problema:** Python 3.14 (única versión instalada) no tenía ruedas precompiladas para `psycopg2-binary` ni para `pydantic-core 2.27.2`, provocando error de compilación por falta de MSVC/Rust.

**Solución:** Migración completa de psycopg2 a **psycopg v3** y actualización de pydantic a la versión con soporte oficial Python 3.14.

**Archivos modificados:**
- `requirements.txt` — Reemplazado `psycopg2-binary==2.9.9` por `psycopg[binary]==3.3.4` + `psycopg-pool==3.3.1`; actualizado `pydantic[email]` de `2.7.4` → `2.13.4` (usa pydantic-core 2.46.4 con ruedas para 3.14).
- `app/database.py` — Reescrito para API psycopg v3: `psycopg_pool.ConnectionPool(conninfo=...)`, `pool.connection()` como context manager, `conn.cursor(row_factory=dict_row)`, `conn.execute()` directo. Eliminado `psycopg2.pool.ThreadedConnectionPool` y `RealDictCursor`.
- `app/routers/photos.py` — Eliminado `psycopg2.Binary(contenido)`; psycopg v3 acepta `bytes` directamente en parámetros.
- `scripts/seed_data.py` — Reemplazado `psycopg2` + `execute_values` por `psycopg` + `cur.executemany()`. Pool de conexiones sustituido por conexión directa `psycopg.connect()`.
- `scripts/concurrency_test.py` — Reescrito para psycopg v3: `psycopg.connect()`, `conn.isolation_level = IsolationLevel.READ_COMMITTED`, `conn.execute()`, manejo de contexto nativo.

**Versiones instaladas finales:**
```
psycopg 3.3.4 + psycopg-binary 3.3.4 + psycopg-pool 3.3.1
pydantic 2.13.4 + pydantic-core 2.46.4
fastapi 0.115.6 + uvicorn 0.32.1
```

---

## ✅ Estado de Módulos Requeridos

| # | Módulo requerido | Estado | Archivo(s) |
|---|-----------------|--------|------------|
| 1 | Volumetría (100K pubs, 10K usuarios) | ✅ Completo | `scripts/seed_data.py` + botón Admin |
| 2 | SQL Procedural y Triggers | ✅ Completo | `02_procedures.sql`, `03_triggers.sql` |
| 3 | Transacciones ACID + créditos | ✅ Completo | `dar_like_publicacion`, `citar_publicacion`, `simular_fallo_creditos` |
| 4 | Control de Concurrencia (50 usuarios) | ✅ Completo | `scripts/concurrency_test.py`, `SELECT FOR UPDATE` |
| 5 | Indexación y Optimización (consultas A/B/C) | ✅ Completo | `04_indexes.sql` + routers |

---
