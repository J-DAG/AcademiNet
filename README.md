# AcademiNet — Manual de Usuario

Red Social Universitaria · Universidad de Cuenca · Base de Datos II

---

## Verificación automática

```bash
python -m pytest -q
```

Las pruebas validan el contrato OpenAPI, los dominios de entrada y los límites de
paginación sin necesitar una base activa. `GET /health` comprueba además PostgreSQL.

---

## Requisitos previos

| Requisito | Versión usada |
|-----------|--------------|
| Python | 3.12 a 3.14 |
| PostgreSQL | 17 o 18 |
| pip | incluido con Python |

---

## Instalación y arranque

```bash
# 1. Crear y activar un entorno virtual
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate

# 2. Instalar dependencias
python -m pip install -r requirements.txt

# 3. Crear la configuración local
# Windows PowerShell
Copy-Item .env.example .env

# Linux/macOS
cp .env.example .env

# 4. Editar .env con el host, puerto, base, usuario y contraseña reales

# Verificar Python, configuración, imágenes y conexión sin modificar datos
python scripts/check_setup.py

# 5. Arrancar la aplicación
python run.py
```

La app queda disponible en **`http://localhost:8000`**

> **Nota:** `.env` es local y no se incluye en Git. PostgreSQL debe tener creada la
> base indicada en `DB_NAME`; el botón **Inicializar BD** crea las tablas, funciones,
> triggers, índices y vistas dentro de esa base.

La carpeta `imagenes/` debe copiarse junto con el proyecto si se desean fotografías
durante el poblado. Si no existe o está vacía, usuarios y publicaciones se generan
normalmente, pero no habrá publicaciones asociadas a imágenes.

Si la base aún no existe, créala desde pgAdmin o desde `psql` conectado a la base
administrativa `postgres`:

```sql
CREATE DATABASE academinet;
```

El nombre debe coincidir con `DB_NAME` en `.env`. Después inicia la aplicación,
abre el Panel de Administración y ejecuta primero **Inicializar BD** y luego
**Poblar Datos**.

---

## Flujo general del programa

```
Usuario abre el navegador
        │
        ▼
  [Página de Inicio]
        │
        ├──► [Panel Admin] ── Inicializar BD ──► ejecuta scripts SQL
        │              │
        │              └──── Poblar Datos ────► genera 10K usuarios
        │                                        y 100K publicaciones
        │
        ├──► [Usuarios] ── Registrar ──► llama a RegistrarUsuarioYCuenta()
        │              │                  (procedimiento PL/pgSQL)
        │              └── Ver / Buscar / Seguir usuarios
        │
        └──► [Publicaciones] ── Crear ──► INSERT + trigger anti-spam
                           │
                           ├── Like ──► dar_like_publicacion()
                           │            transfiere 1 crédito (ACID)
                           └── Citar ──► citar_publicacion()
                                         transfiere 2 créditos (ACID)
```

Toda la lógica crítica vive en la base de datos (procedimientos y triggers).  
FastAPI actúa únicamente como puente entre el navegador y PostgreSQL.

---

## Descripción de cada panel

### Inicio (`/`)

La página principal muestra:

- **Estadísticas en tiempo real** — contadores de usuarios, publicaciones, comentarios, likes y eventos de auditoría. Se cargan automáticamente desde `/api/admin/estadisticas`.
- **Tarjetas de módulos** — descripción rápida de cada funcionalidad implementada (ACID, concurrencia, triggers, indexación, etc.).

---

### Usuarios (`/usuarios-page`)

#### Registrar un usuario

1. Haz clic en **+ Nuevo Usuario**.
2. Completa el formulario:
   - **Cédula** — 10 a 13 dígitos. Debe ser única en el sistema.
   - **Nombres / Apellidos** — texto libre.
   - **Cargo** — solo `profesor` o `investigador` (restricción `CHECK` en la BD).
   - **Email** — opcional.
   - **Tipo de cuenta** — `regular` o `premium`.
3. Haz clic en **Registrar**.

> Internamente se llama al procedimiento `registrar_usuario_y_cuenta(...)` que crea el usuario y su cuenta en una sola transacción. Si la cédula ya existe, el procedimiento captura la excepción y devuelve un mensaje de error sin romper la aplicación.

#### Buscar y navegar

- Escribe en el campo **Buscar** para filtrar por nombre, apellido o cédula en la tabla actual.
- Usa **← Anterior / Siguiente →** para paginar (20 registros por página).

#### Ver créditos

- El ícono 💰 en cada fila muestra los créditos y seguidores actuales del usuario (los créditos se acumulan cuando otros usuarios dan like o citan sus publicaciones).

#### Consulta A — Usuarios activos

- Sección al final de la página.
- Clic en **Ejecutar consulta** para listar todos los profesores/investigadores con más de 10 publicaciones activas.
- Usa el índice compuesto `idx_pub_autor_estado` para eficiencia.

---

### Publicaciones (`/publicaciones-page`)

#### Crear una publicación

1. Haz clic en **+ Nueva Publicación**.
2. Completa:
   - **Título** — obligatorio.
   - **Tipo** — `paper`, `microblog` o `comentario`.
   - **ID Autor** — el `id_usuario` del usuario que publica.
   - **Contenido** — opcional.
3. Haz clic en **Publicar**.

La fotografía es opcional. Una publicación puede contener únicamente texto para
comunicar un resultado esperado, un avance, un hallazgo o una actualización de la
investigación. Durante la población masiva solo cerca del 35% recibe una imagen local.

> El trigger `trg_antispam_publicaciones` impide publicar más de 5 veces en un minuto. Si se supera el límite, la API devuelve un error descriptivo.

#### Filtrar el feed

- Usa los botones de filtro **Todos / Papers / Microblogs / Comentarios** para ver solo un tipo de publicación.
- Las publicaciones se muestran ordenadas por fecha (más recientes primero), 10 por página.
- El filtro de interacciones permite mostrar publicaciones con comentarios, con
  likes o que tengan ambos tipos de interacción. Cada tarjeta indica sus totales de
  likes y comentarios.

#### Dar Like

1. Haz clic en 👍 **Like** en cualquier publicación.
2. Ingresa tu ID de usuario en el modal.
3. Confirma.

> Internamente: `dar_like_publicacion(id_usuario, id_publicacion)` registra el like, **transfiere 1 crédito** del usuario que da like al autor, y registra la transferencia en `transferencias_creditos`. Todo en una sola transacción ACID. No se puede dar like dos veces a la misma publicación ni a las propias.

#### Ver comentarios

- Haz clic en 💬 en cualquier publicación para desplegar/ocultar sus comentarios.
- También puedes introducir `publicaciones.id` en "Buscar por ID". El sistema
  muestra únicamente esa publicación, la resalta y despliega automáticamente todos
  sus comentarios; esto permite revisar fácilmente la publicación utilizada en la
  prueba de concurrencia.

#### Eliminar una publicación

Desde el modal de acciones, el autor puede introducir su ID y seleccionar
`Eliminar publicación`. La operación es un borrado lógico: cambia el estado de
`activo` a `eliminado`, oculta la publicación del feed y conserva sus relaciones
históricas. El trigger registra automáticamente el evento en `auditoria`. Un usuario
distinto del autor no puede ejecutar la eliminación.

---

### Panel de Administración (`/admin-page`)

#### Inicializar Base de Datos

- Ejecuta los 5 scripts SQL en orden:
  1. `01_schema.sql` — crea las 12 tablas con todas sus restricciones.
  2. `02_procedures.sql` — crea 8 funciones PL/pgSQL.
  3. `03_triggers.sql` — crea 5 triggers.
  4. `04_indexes.sql` — crea 17 índices estratégicos.
  5. `05_top_fotografos.sql` — prepara datos demostrativos idempotentes y crea la vista del top 10.
- Solo es necesario la **primera vez**. Si ya existe el schema, los `CREATE TABLE IF NOT EXISTS` y `CREATE INDEX IF NOT EXISTS` lo omiten sin error.

#### Poblar Base de Datos

Genera datos de prueba masivos:

| Dato | Cantidad |
|------|----------|
| Usuarios | 10,000 |
| Cuentas | 10,000 (una por usuario) |
| Publicaciones | 100,000 |
| Relaciones de seguidores | ~2,500 |
| Likes en publicaciones | varía |
| Comentarios | varía |

- **¿Se puede usar más de una vez?** Por defecto **no duplica** — si detecta que ya hay 10K usuarios y 100K publicaciones, se detiene e informa. Si quieres agregar un lote adicional, activa la casilla **Forzar repoblación**.
- El proceso corre en **segundo plano**; la página no se congela. Puede tardar entre 2 y 10 minutos según el equipo.
- El servidor bloquea un segundo intento mientras haya un poblado activo para evitar lotes duplicados.

#### Prueba de Concurrencia

- Lanza 50 hilos simultáneos, cada uno con su propia conexión a PostgreSQL.
- Todos intentan insertar un comentario en la **misma publicación** al mismo tiempo.
- Se usa `SELECT FOR UPDATE` para bloquear la fila de la publicación durante cada transacción, evitando actualizaciones perdidas.
- El nivel de aislamiento es `READ COMMITTED` por defecto (configurable a `SERIALIZABLE` en `scripts/concurrency_test.py`).
- Resultados: transacciones exitosas, fallidas, tiempos promedio/máximo/mínimo.
- El panel muestra el progreso en vivo de 0/50 a 50/50, el tiempo transcurrido,
  la salida del proceso y el estado final. Mientras una prueba está activa, el
  botón queda deshabilitado para impedir ejecuciones duplicadas.
- La misma salida se replica en la terminal donde se ejecutó `python run.py`, por
  lo que el progreso puede observarse simultáneamente en el frontend y en Uvicorn.
- El campo "ID publicación" corresponde a `publicaciones.id` (clave primaria). Si
  se deja vacío, el script selecciona automáticamente una publicación activa; si
  se proporciona, valida y utiliza exactamente esa publicación.

#### Demo ACID — Simulación de Fallo

Demuestra la propiedad de **Atomicidad**:

1. Ingresa ID usuario origen y destino, y un monto de créditos.
2. Si **Forzar fallo** está desactivado: la transferencia se completa normalmente.
3. Si **Forzar fallo** está activado: el sistema descuenta créditos del origen y luego lanza una excepción artificial. El `ROLLBACK` automático revierte el descuento — ambos usuarios quedan con el mismo saldo que antes.

> Esto demuestra que no es posible un estado inconsistente donde el crédito desaparezca a mitad de la operación.

El panel identifica claramente al usuario origen (envía), al destino (recibe) y el
monto. Permite consultar los saldos y presenta una tabla comparativa antes/después.
Cuando se fuerza el fallo, confirma visualmente que ambos saldos permanecieron sin
cambios y que PostgreSQL ejecutó el rollback.
Al terminar cualquier demostración, el panel recarga automáticamente el Log de
Auditoría. Una transferencia confirmada genera un evento; una operación revertida
no genera ninguno, lo que también evidencia la atomicidad de la auditoría.

#### Log de Auditoría

- Muestra los últimos 20 eventos registrados por los triggers de auditoría.
- Eventos capturados automáticamente:
  - **Eliminación de publicación** — trigger `trg_auditoria_eliminacion`
  - **Transferencia confirmada de créditos** — trigger `trg_auditoria_transferencia_creditos`
  - **Registro de fotografía** — trigger `trg_auditoria_registro_fotografia`
- El panel incluye “Eliminar Publicación y Auditar”: solicita únicamente el ID de
  la publicación, obtiene internamente su autor, ejecuta el borrado lógico y recarga
  automáticamente el log para mostrar el evento generado.
- El log mantiene una altura máxima y utiliza desplazamiento vertical interno, con
  el encabezado de la tabla fijo para facilitar la revisión de múltiples eventos.

#### Consultas de Optimización

Tres consultas complejas ejecutadas sobre la BD con sus índices aplicados:

Cada consulta dispone de `Ejecutar y analizar`, que muestra conjuntamente los
resultados, el tiempo de respuesta de la API y el plan técnico: costo inicial/final,
tiempos de planificación y ejecución, buffers, filas, nodos e índices utilizados.
El análisis no elimina ni crea índices desde el frontend.

| Botón | Consulta | Índice principal usado |
|-------|----------|----------------------|
| **A: Usuarios activos** | Profesores/investigadores con más de 10 publicaciones | `idx_pub_autor_estado` |
| **B: Top fotógrafos** | Top 10 usuarios con más fotos cuyas pubs recibieron >50 comentarios en el último mes | `idx_com_pub_fecha`, `idx_foto_usuario` |
| **C: Fotos + interacciones** | Fotografías ordenadas por likes + comentarios | `idx_foto_likes` |

> Para el informe de rendimiento: ejecuta estas mismas consultas con `EXPLAIN ANALYZE` en pgAdmin antes y después de crear los índices y captura los planes de ejecución.

El reporte B también está disponible como script independiente en
`database/05_top_fotografos.sql`. Este genera de forma idempotente los comentarios
demostrativos necesarios para que diez autores con fotografías superen el umbral,
crea `vw_top_fotografos` y ejecuta el reporte final del top 10.

---

## API REST — Documentación interactiva

Disponible en **`http://localhost:8000/docs`** (Swagger UI generado automáticamente por FastAPI).

Desde ahí puedes probar cualquier endpoint directamente en el navegador sin necesidad de herramientas externas.

---

## Estructura de la base de datos (resumen)

```
usuarios ──┬── cuentas
           ├── publicaciones ──┬── comentarios
           │                   ├── likes_publicaciones
           │                   └── citaciones
           ├── fotografias ────┬── comentarios_foto
           │                   └── likes_fotografias
           └── seguidores (relación muchos a muchos)

transferencias_creditos  ← registro de movimientos ACID
auditoria                ← log automático de triggers
```

---

## Comandos útiles de mantenimiento

```bash
# Ver logs de la app en tiempo real
python run.py

# Poblar datos manualmente desde la terminal
python scripts/seed_data.py

# Importar la carpeta local imagenes/ como objetos BYTEA (reanudable)
python scripts/import_images.py

# Optimizar y generar miniaturas para fotografías ya almacenadas
python scripts/optimize_existing_images.py

# Poblar forzando un lote adicional
SEED_FORZAR=1 python scripts/seed_data.py   # Linux/Mac
$env:SEED_FORZAR="1"; python scripts/seed_data.py  # Windows PowerShell

# Ejecutar prueba de concurrencia manualmente
python scripts/concurrency_test.py

# Conectar a la BD directamente
psql -U <DB_USER> -p <DB_PORT> -d <DB_NAME>
```

---

## Informe de rendimiento — resultados medidos

Las consultas A, B y C se ejecutaron mediante:

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)
```

Se realizaron mediciones antes y después de crear los índices estratégicos de
`database/04_indexes.sql`. El costo es una estimación interna de PostgreSQL; el
tiempo real se toma siempre de `Execution Time`.

### Tabla comparativa completa

| Consulta | Estado | Costo inicial | Costo final | Tiempo | Plan principal | Buffers |
|---|---|---:|---:|---:|---|---|
| A | Sin índices | 6088.64 | 6096.97 | 89.929 ms | Sort → HashAggregate → Hash Join → Seq Scan | hit=3534 |
| A | Con índices | 6088.64 | 6096.97 | 67.774 ms | Sort → HashAggregate → Hash Join → Seq Scan | hit=3531 |
| B | Sin índices | 1337.53 | 1337.56 | 1.071 ms | Limit → Sort → GroupAggregate → Nested Loop | hit=1022 |
| B | Con índices | 1336.92 | 1336.94 | 1.065 ms | Limit → Sort → GroupAggregate → Nested Loop | hit=1022 |
| C | Sin índices | 7374.35 | 7376.68 | 142.056 ms | Limit → Gather Merge → Parallel Seq Scan | hit=3825 |
| C | Con índices | 7358.78 | 7361.11 | 44.976 ms | Limit → Gather Merge → Parallel Bitmap Heap Scan | hit=1842, read=31 |

La mejora porcentual se calculó mediante:

```text
Mejora (%) = ((valor_sin_índice - valor_con_índice) / valor_sin_índice) × 100
```

### Resumen de resultados

| Consulta | Tiempo sin índices | Tiempo con índices | Variación temporal | Reducción del costo final | Índice estratégico utilizado |
|---|---:|---:|---:|---:|---|
| A: usuarios activos | 89.929 ms | 67.774 ms | 24.64% | 0.00% | Ninguno |
| B: top fotógrafos | 1.071 ms | 1.065 ms | 0.56% | 0.05% | Ninguno |
| C: fotos con interacciones | 142.056 ms | 44.976 ms | 68.34% | 0.21% | `idx_pub_id_foto` |

> La reducción temporal de A no se atribuye directamente a los índices porque el
> costo y el plan fueron idénticos. La causa más probable es el calentamiento de
> caché entre ejecuciones.

### Análisis de la consulta A

El plan antes y después de crear los índices fue:

```text
Sort
└── HashAggregate
    └── Hash Join
        ├── Seq Scan publicaciones
        └── Seq Scan usuarios
```

PostgreSQL leyó las 100,000 publicaciones porque todas cumplían la condición
`estado = 'activo'`. El índice `idx_pub_autor_estado` no fue seleccionado debido a
que la consulta necesitaba procesar prácticamente toda la tabla. En ese escenario,
un recorrido secuencial resulta menos costoso que múltiples accesos mediante un
índice.

El costo permaneció exactamente igual:

```text
Sin índices: 6088.64..6096.97
Con índices: 6088.64..6096.97
```

Conclusión para el informe:

> En la consulta A, la creación de índices no modificó el costo estimado ni el plan
> de ejecución. PostgreSQL mantuvo un `Sequential Scan` sobre las 100,000
> publicaciones debido a que todas cumplían la condición `estado = 'activo'`. La
> reducción temporal de 89.929 ms a 67.774 ms se atribuye principalmente al
> calentamiento de caché y no al uso de un índice estratégico.

### Análisis de la consulta B

El plan general fue equivalente en ambas mediciones:

```text
Limit
└── Sort
    └── GroupAggregate
        └── Nested Loop
            ├── Seq Scan comentarios
            ├── Index Scan publicaciones_pkey
            └── Index Scan usuarios_pkey
```

La consulta produjo cero resultados porque ningún usuario superó el umbral de 50
comentarios en el periodo evaluado. La tabla `comentarios` tenía 793 registros, de
los cuales 372 correspondían al último mes. Por su reducido tamaño, PostgreSQL
prefirió recorrerla secuencialmente.

Los índices `publicaciones_pkey` y `usuarios_pkey` fueron utilizados, pero estos son
índices automáticos asociados a claves primarias y no forman parte de los índices
estratégicos de `04_indexes.sql`.

Conclusión para el informe:

> La consulta B presentó una reducción de costo de aproximadamente 0.05% y una
> reducción temporal de 0.56%, por lo que no existe una mejora significativa.
> PostgreSQL mantuvo un escaneo secuencial sobre `comentarios` debido a que la tabla
> solo contenía 793 registros. Los únicos índices empleados fueron los asociados a
> las claves primarias de `publicaciones` y `usuarios`.

### Análisis de la consulta C

Sin índices, PostgreSQL realizó un recorrido paralelo sobre las 100,000
publicaciones:

```text
Gather Merge
└── Sort
    └── Hash Join
        └── Parallel Seq Scan publicaciones
```

Después de crear los índices, el plan incluyó:

```text
Parallel Bitmap Heap Scan on publicaciones
└── Bitmap Index Scan on idx_pub_id_foto
```

`idx_pub_id_foto` permitió localizar directamente las 35,000 publicaciones que
tenían una fotografía, en lugar de recorrer las 100,000 publicaciones. El tiempo
bajó de 142.056 ms a 44.976 ms, una mejora del 68.34%.

Los buffers pasaron de 3,825 páginas a 1,873 páginas:

```text
Sin índices: 3825 hit
Con índices: 1842 hit + 31 read = 1873 páginas
Reducción aproximada: 51.03%
```

Conclusión para el informe:

> La consulta C presentó la mejora más significativa. Sin índices, PostgreSQL
> realizó un `Parallel Sequential Scan` sobre las 100,000 publicaciones. Después de
> crear `idx_pub_id_foto`, el optimizador cambió a un `Bitmap Index Scan` seguido de
> un `Parallel Bitmap Heap Scan`, localizando directamente las 35,000 publicaciones
> con fotografía. El tiempo de ejecución se redujo de 142.056 ms a 44.976 ms,
> equivalente a una mejora del 68.34%. La cantidad de páginas procesadas disminuyó
> aproximadamente un 51.03%.

### Evidencias gráficas pendientes

Guardar las capturas con los siguientes nombres:

```text
A_sin_indices_plan.png
A_sin_indices_tiempo.png
A_con_indices_plan.png
A_con_indices_tiempo.png
B_sin_indices_plan.png
B_sin_indices_tiempo.png
B_con_indices_plan.png
B_con_indices_tiempo.png
C_sin_indices_plan.png
C_sin_indices_tiempo.png
C_con_indices_plan.png
C_con_indices_tiempo.png
```

Las capturas deben mostrar el nombre de la base `academinet`, el nodo principal del
plan, el tipo de escaneo, el índice utilizado cuando corresponda, `Planning Time`,
`Execution Time` y los buffers. Para la consulta C con índices, la evidencia más
importante es:

```text
Parallel Bitmap Heap Scan on publicaciones
Bitmap Index Scan on idx_pub_id_foto
Execution Time: 44.976 ms
```
