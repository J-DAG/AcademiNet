# AcademiNet — Manual de Usuario

Red Social Universitaria · Universidad de Cuenca · Base de Datos II

---

## Requisitos previos

| Requisito | Versión usada |
|-----------|--------------|
| Python | 3.14 |
| PostgreSQL | 17.5 |
| pip | incluido con Python |

---

## Instalación y arranque

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Arrancar la aplicación
python run.py
```

La app queda disponible en **`http://localhost:8000`**

> **Nota:** El archivo `.env` ya está configurado con los datos de conexión.  
> Si cambias el servidor, edítalo antes de arrancar.

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

> El trigger `trg_antispam_publicaciones` impide publicar más de 5 veces en un minuto. Si se supera el límite, la API devuelve un error descriptivo.

#### Filtrar el feed

- Usa los botones de filtro **Todos / Papers / Microblogs / Comentarios** para ver solo un tipo de publicación.
- Las publicaciones se muestran ordenadas por fecha (más recientes primero), 10 por página.

#### Dar Like

1. Haz clic en 👍 **Like** en cualquier publicación.
2. Ingresa tu ID de usuario en el modal.
3. Confirma.

> Internamente: `dar_like_publicacion(id_usuario, id_publicacion)` registra el like, **transfiere 1 crédito** del usuario que da like al autor, y registra la transferencia en `transferencias_creditos`. Todo en una sola transacción ACID. No se puede dar like dos veces a la misma publicación ni a las propias.

#### Ver comentarios

- Haz clic en 💬 en cualquier publicación para desplegar/ocultar sus comentarios.

---

### Panel de Administración (`/admin-page`)

#### Inicializar Base de Datos

- Ejecuta los 4 scripts SQL en orden:
  1. `01_schema.sql` — crea las 12 tablas con todas sus restricciones.
  2. `02_procedures.sql` — crea 8 funciones PL/pgSQL.
  3. `03_triggers.sql` — crea 5 triggers.
  4. `04_indexes.sql` — crea 16 índices estratégicos.
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

#### Prueba de Concurrencia

- Lanza 50 hilos simultáneos, cada uno con su propia conexión a PostgreSQL.
- Todos intentan insertar un comentario en la **misma publicación** al mismo tiempo.
- Se usa `SELECT FOR UPDATE` para bloquear la fila de la publicación durante cada transacción, evitando actualizaciones perdidas.
- El nivel de aislamiento es `READ COMMITTED` por defecto (configurable a `SERIALIZABLE` en `scripts/concurrency_test.py`).
- Resultados: transacciones exitosas, fallidas, tiempos promedio/máximo/mínimo.

#### Demo ACID — Simulación de Fallo

Demuestra la propiedad de **Atomicidad**:

1. Ingresa ID usuario origen y destino, y un monto de créditos.
2. Si **Forzar fallo** está desactivado: la transferencia se completa normalmente.
3. Si **Forzar fallo** está activado: el sistema descuenta créditos del origen y luego lanza una excepción artificial. El `ROLLBACK` automático revierte el descuento — ambos usuarios quedan con el mismo saldo que antes.

> Esto demuestra que no es posible un estado inconsistente donde el crédito desaparezca a mitad de la operación.

#### Log de Auditoría

- Muestra los últimos 20 eventos registrados por los triggers de auditoría.
- Eventos capturados automáticamente:
  - **Cambio de foto de perfil** — trigger `trg_auditoria_foto_perfil`
  - **Eliminación de publicación** — trigger `trg_auditoria_eliminacion`

#### Consultas de Optimización

Tres consultas complejas ejecutadas sobre la BD con sus índices aplicados:

| Botón | Consulta | Índice principal usado |
|-------|----------|----------------------|
| **A: Usuarios activos** | Profesores/investigadores con más de 10 publicaciones | `idx_pub_autor_estado` |
| **B: Top fotógrafos** | Top 10 usuarios con más fotos cuyas pubs recibieron >50 comentarios en el último mes | `idx_com_pub_fecha`, `idx_foto_usuario` |
| **C: Fotos + interacciones** | Fotografías ordenadas por likes + comentarios | `idx_foto_likes` |

> Para el informe de rendimiento: ejecuta estas mismas consultas con `EXPLAIN ANALYZE` en pgAdmin antes y después de crear los índices y captura los planes de ejecución.

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

# Poblar forzando un lote adicional
SEED_FORZAR=1 python scripts/seed_data.py   # Linux/Mac
$env:SEED_FORZAR="1"; python scripts/seed_data.py  # Windows PowerShell

# Ejecutar prueba de concurrencia manualmente
python scripts/concurrency_test.py

# Conectar a la BD directamente
psql -U postgres -p 5434 -d academinet
```
