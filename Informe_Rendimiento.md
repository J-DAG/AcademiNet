# Informe de Rendimiento — AcademiNet

## 1. Objetivo

Evaluar el efecto de los índices estratégicos de PostgreSQL sobre tres consultas
representativas de AcademiNet, comparando costo estimado, tiempo real, buffers y
plan de ejecución antes y después de crear los índices.

## 2. Entorno y volumetría

- Motor: PostgreSQL 18.3.
- Backend: Python 3.14, FastAPI y psycopg 3.
- Usuarios: 10,000.
- Cuentas: 10,000.
- Publicaciones: 100,000.
- Publicaciones con fotografía: 35,000.
- Fotografías: 463.
- Comentarios: 1,743, incluidos los datos demostrativos y pruebas de concurrencia.
- Likes de publicaciones: 7,313.
- Índices estratégicos evaluados: 15.

La volumetría puede comprobarse con:

```sql
SELECT
    (SELECT COUNT(*) FROM usuarios) AS usuarios,
    (SELECT COUNT(*) FROM cuentas) AS cuentas,
    (SELECT COUNT(*) FROM publicaciones) AS publicaciones,
    (SELECT COUNT(*) FROM publicaciones WHERE id_foto IS NOT NULL) AS publicaciones_con_foto,
    (SELECT COUNT(*) FROM fotografias) AS fotografias,
    (SELECT COUNT(*) FROM comentarios) AS comentarios,
    (SELECT COUNT(*) FROM likes_publicaciones) AS likes;
```

## 3. Metodología

1. Se eliminaron únicamente los 15 índices estratégicos `idx_*`.
2. No se eliminaron índices de claves primarias ni restricciones `UNIQUE`.
3. Se ejecutó `ANALYZE` sobre las tablas involucradas.
4. Se fijó `max_parallel_workers_per_gather = 0` para aislar el efecto de los
   índices y reducir variaciones producidas por el arranque de workers paralelos.
5. Cada consulta se ejecutó tres veces mediante:

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
```

6. Se utilizó la mediana de los tres tiempos.
7. Se restauraron los 15 índices y se repitió el procedimiento.

El experimento completo puede reproducirse con:

```powershell
python scripts/benchmark_indexes.py
```

El script restaura los índices dentro de un bloque `finally`, incluso si una
medición falla.

### 3.1 Índices eliminados para el escenario base

Para obtener el escenario "sin índices" se eliminaron únicamente los 15 índices
estratégicos. No se tocaron claves primarias ni índices creados por restricciones
`UNIQUE`.

```sql
DROP INDEX IF EXISTS idx_pub_autor;
DROP INDEX IF EXISTS idx_pub_fecha;
DROP INDEX IF EXISTS idx_pub_autor_estado;
DROP INDEX IF EXISTS idx_pub_tipo;
DROP INDEX IF EXISTS idx_pub_id_foto;
DROP INDEX IF EXISTS idx_com_publicacion;
DROP INDEX IF EXISTS idx_com_pub_fecha;
DROP INDEX IF EXISTS idx_com_usuario;
DROP INDEX IF EXISTS idx_foto_usuario;
DROP INDEX IF EXISTS idx_likes_pub_pub;
DROP INDEX IF EXISTS idx_likes_pub_usr;
DROP INDEX IF EXISTS idx_usr_cargo;
DROP INDEX IF EXISTS idx_usr_email;
DROP INDEX IF EXISTS idx_tc_origen;
DROP INDEX IF EXISTS idx_tc_destino;
```

### 3.2 Estadísticas y configuración de la sesión

Después de eliminar y después de restaurar los índices se ejecutó:

```sql
ANALYZE usuarios;
ANALYZE publicaciones;
ANALYZE fotografias;
ANALYZE comentarios;
ANALYZE likes_publicaciones;
ANALYZE transferencias_creditos;
```

Para aislar el efecto de los índices y reducir la variación de workers paralelos:

```sql
SET max_parallel_workers_per_gather = 0;
```

### 3.3 Índices restaurados

Para el escenario "con índices" se recrearon:

```sql
CREATE INDEX IF NOT EXISTS idx_pub_autor ON publicaciones (autor);
CREATE INDEX IF NOT EXISTS idx_pub_fecha ON publicaciones (fecha_publicacion DESC);
CREATE INDEX IF NOT EXISTS idx_pub_autor_estado
    ON publicaciones (autor, estado) WHERE estado = 'activo';
CREATE INDEX IF NOT EXISTS idx_pub_tipo ON publicaciones (tipo);
CREATE INDEX IF NOT EXISTS idx_pub_id_foto
    ON publicaciones (id_foto) WHERE id_foto IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_com_publicacion ON comentarios (id_publicacion);
CREATE INDEX IF NOT EXISTS idx_com_pub_fecha
    ON comentarios (id_publicacion, fecha_comentario DESC);
CREATE INDEX IF NOT EXISTS idx_com_usuario ON comentarios (id_usuario);

CREATE INDEX IF NOT EXISTS idx_foto_usuario ON fotografias (id_usuario);
CREATE INDEX IF NOT EXISTS idx_likes_pub_pub ON likes_publicaciones (id_publicacion);
CREATE INDEX IF NOT EXISTS idx_likes_pub_usr ON likes_publicaciones (id_usuario);
CREATE INDEX IF NOT EXISTS idx_usr_cargo ON usuarios (cargo);
CREATE INDEX IF NOT EXISTS idx_usr_email ON usuarios (email);
CREATE INDEX IF NOT EXISTS idx_tc_origen ON transferencias_creditos (id_usuario_origen);
CREATE INDEX IF NOT EXISTS idx_tc_destino ON transferencias_creditos (id_usuario_destino);
```

## 4. Consultas evaluadas

### Consulta A — Usuarios activos

Lista profesores o investigadores con más de diez publicaciones activas.

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT u.id_usuario, u.nombres, u.apellidos, u.cargo,
       COUNT(p.id) AS total_pubs
FROM usuarios u
JOIN publicaciones p
  ON p.autor = u.id_usuario AND p.estado = 'activo'
GROUP BY u.id_usuario, u.nombres, u.apellidos, u.cargo
HAVING COUNT(p.id) > 10
ORDER BY total_pubs DESC;
```

### Consulta B — Top fotógrafos

Lista los diez autores con más fotografías cuyas publicaciones recibieron más de
50 comentarios durante el último mes.

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT u.id_usuario, u.nombres, u.apellidos,
       COUNT(DISTINCT p.id_foto) AS total_fotos,
       COUNT(DISTINCT c.id_comentario) AS total_comentarios
FROM usuarios u
JOIN publicaciones p
  ON p.autor = u.id_usuario
 AND p.estado = 'activo'
 AND p.id_foto IS NOT NULL
JOIN comentarios c
  ON c.id_publicacion = p.id
 AND c.fecha_comentario >= NOW() - INTERVAL '1 month'
GROUP BY u.id_usuario, u.nombres, u.apellidos
HAVING COUNT(DISTINCT c.id_comentario) > 50
ORDER BY total_fotos DESC
LIMIT 10;
```

### Consulta C — Fotografías con interacciones

Lista publicaciones con fotografía ordenadas por la suma de likes y comentarios.
Likes y comentarios se preagrupan antes del `JOIN` para evitar multiplicación de
filas.

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
WITH likes AS (
    SELECT id_publicacion, COUNT(*) AS total_likes
    FROM likes_publicaciones
    GROUP BY id_publicacion
), comentarios_agrupados AS (
    SELECT id_publicacion, COUNT(*) AS total_comentarios
    FROM comentarios
    GROUP BY id_publicacion
)
SELECT p.id, p.titulo,
       (u.nombres || ' ' || u.apellidos) AS autor,
       f.id_foto,
       COALESCE(l.total_likes, 0)
         + COALESCE(c.total_comentarios, 0) AS total_interacciones
FROM publicaciones p
JOIN fotografias f ON f.id_foto = p.id_foto
JOIN usuarios u ON u.id_usuario = p.autor
LEFT JOIN likes l ON l.id_publicacion = p.id
LEFT JOIN comentarios_agrupados c ON c.id_publicacion = p.id
WHERE p.estado = 'activo'
ORDER BY total_interacciones DESC
LIMIT 20;
```

## 5. Resultados

### 5.1 Tabla comparativa

| Consulta | Estado | Costo inicial | Costo final | Mediana | Ejecuciones | Buffers hit | Índices usados |
|---|---|---:|---:|---:|---|---:|---|
| A | Sin índices | 6088.64 | 6096.97 | 72.387 ms | 75.505 / 54.148 / 72.387 | 3531 | Ninguno |
| A | Con índices | 6088.64 | 6096.97 | 79.301 ms | 70.383 / 79.301 / 82.590 | 3531 | Ninguno |
| B | Sin índices | 1350.34 | 1350.36 | 2.704 ms | 2.976 / 2.704 / 2.551 | 3010 | PK de publicaciones y usuarios |
| B | Con índices | 1352.27 | 1352.30 | 2.504 ms | 2.548 / 2.504 / 2.376 | 3010 | PK de publicaciones y usuarios |
| C | Sin índices | 9734.94 | 9734.99 | 53.380 ms | 53.310 / 53.380 / 59.383 | 3615 | Ninguno |
| C | Con índices | 9252.54 | 9252.59 | 36.743 ms | 36.407 / 36.743 / 39.675 | 1469 | `idx_pub_id_foto` |

### 5.2 Variación

La mejora se calculó mediante:

```text
Mejora (%) = ((sin_índices - con_índices) / sin_índices) × 100
```

| Consulta | Variación del tiempo | Reducción del costo final | Reducción de buffers |
|---|---:|---:|---:|
| A | -9.55% | 0.00% | 0.00% |
| B | 7.40% | -0.14% | 0.00% |
| C | 31.17% | 4.96% | 59.36% |

Un porcentaje temporal negativo significa que la ejecución con índices fue más
lenta. No debe interpretarse como mejora.

## 6. Análisis de planes

### 6.1 Consulta A

Plan general en ambos escenarios:

```text
Sort
└── Aggregate
    └── Hash Join
        ├── Seq Scan publicaciones
        └── Seq Scan usuarios
```

El costo y los buffers no cambiaron. PostgreSQL no utilizó
`idx_pub_autor_estado` porque las 100,000 publicaciones estaban activas y la
consulta debía procesar prácticamente toda la tabla. Un índice tiene baja
selectividad en este escenario y el `Sequential Scan` resulta más económico.

La diferencia temporal de -9.55% es variación de ejecución y no un efecto del
índice, ya que el plan y el costo son idénticos.

### 6.2 Consulta B

Plan general:

```text
Limit
└── Sort
    └── Aggregate
        └── Nested Loop
            ├── Seq Scan comentarios
            ├── Index Scan publicaciones_pkey
            └── Index Scan usuarios_pkey
```

La consulta mejoró 7.40%, pero no utilizó un índice estratégico. Los índices que
aparecen son los creados automáticamente por las claves primarias. La tabla de
comentarios es pequeña respecto de publicaciones, por lo que PostgreSQL prefiere
recorrerla secuencialmente.

### 6.3 Consulta C

Sin índices:

```text
Limit
└── Sort
    └── Hash Join
        └── Seq Scan publicaciones
```

Con índices:

```text
Limit
└── Sort
    └── Hash Join
        └── Bitmap Heap Scan publicaciones
            └── Bitmap Index Scan idx_pub_id_foto
```

`idx_pub_id_foto` localizó directamente las publicaciones con fotografía. El
tiempo se redujo de 53.380 ms a 36.743 ms, el costo final de 9734.99 a 9252.59 y
los buffers de 3615 a 1469. Esta es la evidencia principal de mejora por
indexación.

## 7. Justificación de índices

| Índice | Justificación |
|---|---|
| `idx_pub_autor` | Consultas de publicaciones por autor. |
| `idx_pub_fecha` | Feed ordenado por fecha descendente. |
| `idx_pub_autor_estado` | Publicaciones activas agrupadas o filtradas por autor. |
| `idx_pub_tipo` | Filtros de paper, microblog y comentario. |
| `idx_pub_id_foto` | Localiza publicaciones con fotografía; utilizado por C. |
| `idx_com_publicacion` | Comentarios asociados a una publicación. |
| `idx_com_pub_fecha` | Comentarios de una publicación dentro de un periodo. |
| `idx_com_usuario` | Actividad de comentarios por usuario. |
| `idx_foto_usuario` | Fotografías registradas por usuario. |
| `idx_likes_pub_pub` | Likes y conteos por publicación. |
| `idx_likes_pub_usr` | Likes realizados por usuario. |
| `idx_usr_cargo` | Filtros de profesores e investigadores. |
| `idx_usr_email` | Búsquedas por correo electrónico. |
| `idx_tc_origen` | Historial de créditos enviados. |
| `idx_tc_destino` | Historial de créditos recibidos. |

## 8. Justificación del protocolo de control de concurrencia

### 8.1 Protocolo seleccionado

AcademiNet utiliza un protocolo híbrido compuesto por el nivel de aislamiento
`READ COMMITTED` de PostgreSQL y bloqueos pesimistas de fila mediante
`SELECT ... FOR UPDATE`. Cada operación se ejecuta en una transacción independiente
y finaliza con `COMMIT` cuando tiene éxito o con `ROLLBACK` cuando ocurre un error.

`READ COMMITTED` aplica el mecanismo MVCC (*Multi-Version Concurrency Control*) de
PostgreSQL: cada sentencia solamente puede observar datos confirmados antes de que
comience esa sentencia. Por tanto, evita las lecturas sucias sin bloquear las
consultas ordinarias de lectura.

El bloqueo `FOR UPDATE` se agrega en los puntos donde una operación debe leer un
estado y modificarlo de forma consistente. Si otra transacción intenta bloquear la
misma fila, debe esperar hasta que la primera confirme o revierta sus cambios.

### 8.2 Aplicación en AcademiNet

En la prueba de concurrencia, 50 hilos abren conexiones independientes e intentan
insertar un comentario sobre la misma publicación. Antes de insertar, cada
transacción ejecuta:

```sql
SELECT id
FROM publicaciones
WHERE id = :id_publicacion AND estado = 'activo'
FOR UPDATE;
```

Este bloqueo serializa el acceso crítico a la publicación. Así, una transacción no
puede validar la publicación mientras otra la está modificando o eliminando
lógicamente. El bloqueo se libera automáticamente al ejecutar `COMMIT` o
`ROLLBACK`; no depende de una liberación manual desde Python.

El mismo criterio se aplica a las transferencias de créditos producidas por likes,
citaciones y por el demo ACID. Las cuentas involucradas se bloquean antes de leer
el saldo y actualizarlo:

```sql
SELECT 1
FROM cuentas
WHERE id_usuario IN (:origen, :destino)
ORDER BY id_usuario
FOR UPDATE;
```

El orden ascendente por `id_usuario` hace que las transacciones soliciten los
bloqueos en un orden determinista, lo que reduce el riesgo de interbloqueos cuando
dos operaciones afectan las mismas cuentas en sentido contrario.

### 8.3 Problemas que evita

El protocolo elegido proporciona las siguientes garantías:

- Evita lecturas sucias porque `READ COMMITTED` solo expone datos confirmados.
- Evita actualizaciones perdidas sobre los saldos, porque una segunda transacción
  debe esperar antes de volver a leer y modificar una cuenta bloqueada.
- Impide validar una publicación activa mientras otra transacción mantiene
  bloqueada esa misma fila para modificarla.
- Conserva la atomicidad: el comentario o la transferencia se confirma por
  completo; ante una excepción, sus modificaciones se revierten.
- Reduce la posibilidad de *deadlock* al bloquear las cuentas siempre en el mismo
  orden.

El `threading.Lock` presente en el script se utiliza únicamente para proteger los
contadores y la salida compartida de Python. La integridad de los datos la garantiza
PostgreSQL mediante sus transacciones y bloqueos de fila.

### 8.4 Razón para usar READ COMMITTED

Se seleccionó `READ COMMITTED` porque ofrece un equilibrio adecuado entre
consistencia y rendimiento para una red social: permite que operaciones sobre
publicaciones diferentes avancen simultáneamente y concentra la espera solamente
en las filas que realmente compiten. Utilizar `SERIALIZABLE` para todas las
operaciones aumentaría la protección frente a anomalías complejas, pero también
podría generar más abortos, reintentos y costo operativo bajo una carga elevada.

Los bloqueos pesimistas sí reducen temporalmente la concurrencia cuando los 50
hilos trabajan sobre la misma publicación. Esta serialización es intencional en la
prueba, pues representa el peor caso de contención y prioriza la consistencia. En
el uso normal, las operaciones se distribuyen entre múltiples publicaciones y el
bloqueo de una fila no detiene las transacciones sobre otras filas.

### 8.5 Validación experimental

La prueba se ejecuta con `scripts/concurrency_test.py` o desde el módulo
Administración. Para documentarla se debe registrar:

- Nivel de aislamiento mostrado: `READ_COMMITTED`.
- Número de conexiones o hilos: 50.
- Identificador de la publicación objetivo.
- Transacciones exitosas y fallidas.
- Tiempo total, promedio, mínimo y máximo.
- Cantidad de comentarios antes y después de la ejecución.

Si las 50 transacciones finalizan correctamente, el contador de comentarios debe
aumentar exactamente en 50. Un resultado diferente debe justificarse con los
errores reportados por el script. Como prueba adicional, el nivel puede cambiarse
a `SERIALIZABLE`; en ese escenario la aplicación debería contemplar reintentos para
las transacciones que PostgreSQL cancele por conflictos de serialización.

## 9. Capturas requeridas

Las capturas constituyen la evidencia visual de la ejecución de las pruebas. Se
recomienda guardarlas en una carpeta `capturas_rendimiento/`, con los siguientes
nombres consistentes:

```text
01_volumetria.png
02_A_sin_indices.png
03_A_con_indices.png
04_B_sin_indices.png
05_B_con_indices.png
06_C_sin_indices.png
07_C_con_indices.png
08_prueba_concurrencia.png
```

### 9.1 Tabla de control de evidencias

| N.º | Captura | Evidencia que debe mostrar | Estado |
|---:|---|---|:---:|
| 1 | `01_volumetria.png` | Cantidad de registros de las tablas evaluadas. | Pendiente |
| 2 | `02_A_sin_indices.png` | Plan y tiempo de la consulta A antes de crear los índices. | Pendiente |
| 3 | `03_A_con_indices.png` | Plan y tiempo de la consulta A con los índices creados. | Pendiente |
| 4 | `04_B_sin_indices.png` | Plan y tiempo de la consulta B antes de crear los índices. | Pendiente |
| 5 | `05_B_con_indices.png` | Plan y tiempo de la consulta B con los índices creados. | Pendiente |
| 6 | `06_C_sin_indices.png` | Plan y tiempo de la consulta C antes de crear los índices. | Pendiente |
| 7 | `07_C_con_indices.png` | Uso de `idx_pub_id_foto` y métricas finales de la consulta C. | Pendiente |
| 8 | `08_prueba_concurrencia.png` | Resultado de los 50 hilos, nivel de aislamiento y tiempos. | Pendiente |

Cambiar **Pendiente** por **Incluida** a medida que se incorporen las imágenes al
documento final.

### 9.2 Espacios para insertar las capturas

#### Figura 1. Volumetría de la base de datos

> **Insertar aquí:** `capturas_rendimiento/01_volumetria.png`

**Pie de figura:** Figura 1. Cantidad de registros existentes en las tablas
principales de AcademiNet al momento de ejecutar las pruebas de rendimiento.

#### Figura 2. Consulta A sin índices estratégicos

> **Insertar aquí:** `capturas_rendimiento/02_A_sin_indices.png`

**Pie de figura:** Figura 2. Plan de ejecución de la consulta A sin índices
estratégicos, incluyendo costo estimado, tiempo real, buffers y tipo de escaneo.

#### Figura 3. Consulta A con índices estratégicos

> **Insertar aquí:** `capturas_rendimiento/03_A_con_indices.png`

**Pie de figura:** Figura 3. Plan de ejecución de la consulta A después de crear
los índices estratégicos.

#### Figura 4. Consulta B sin índices estratégicos

> **Insertar aquí:** `capturas_rendimiento/04_B_sin_indices.png`

**Pie de figura:** Figura 4. Plan de ejecución de la consulta B sin índices
estratégicos, mostrando los índices de clave primaria utilizados por PostgreSQL.

#### Figura 5. Consulta B con índices estratégicos

> **Insertar aquí:** `capturas_rendimiento/05_B_con_indices.png`

**Pie de figura:** Figura 5. Plan de ejecución de la consulta B después de crear
los índices estratégicos.

#### Figura 6. Consulta C sin índices estratégicos

> **Insertar aquí:** `capturas_rendimiento/06_C_sin_indices.png`

**Pie de figura:** Figura 6. Plan de ejecución de la consulta C sin índices
estratégicos, usado como línea base para la comparación.

#### Figura 7. Consulta C con índices estratégicos

> **Insertar aquí:** `capturas_rendimiento/07_C_con_indices.png`

**Pie de figura:** Figura 7. Plan optimizado de la consulta C con el índice
`idx_pub_id_foto`, junto con la reducción del tiempo de ejecución y de los buffers.

#### Figura 8. Prueba de control de concurrencia

> **Insertar aquí:** `capturas_rendimiento/08_prueba_concurrencia.png`

**Pie de figura:** Figura 8. Ejecución concurrente de 50 transacciones sobre una
misma publicación utilizando `READ COMMITTED` y bloqueo de fila con
`SELECT FOR UPDATE`.

### 9.3 Requisitos de cada captura

Cada captura debe mostrar:

- Base `academinet` seleccionada.
- Consulta ejecutada.
- Nodo principal.
- Tipo de escaneo.
- Índice utilizado, cuando corresponda.
- `Planning Time`.
- `Execution Time`.
- Buffers.

La imagen debe ser legible, no debe recortar el nodo principal ni las métricas
finales y, de ser posible, debe incluir el nombre de la consulta en el editor SQL.
No es necesario capturar todas las filas del resultado; la evidencia relevante es
el plan producido por `EXPLAIN (ANALYZE, BUFFERS, VERBOSE)`.

La captura principal es C con índices, donde debe aparecer:

```text
Bitmap Index Scan on idx_pub_id_foto
```

## 10. Conclusiones

Los índices no mejoran automáticamente todas las consultas. Su utilidad depende de
la selectividad, el tamaño de las tablas y la proporción de filas leídas.

- A procesa casi toda la tabla y conserva `Sequential Scan`.
- B trabaja con pocos comentarios y utiliza principalmente índices de PK.
- C reduce 31.17% el tiempo y 59.36% los buffers mediante
  `idx_pub_id_foto`.

La evaluación demuestra tanto un caso favorable como casos donde PostgreSQL decide
correctamente no utilizar índices estratégicos.
