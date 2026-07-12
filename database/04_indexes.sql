-- ============================================================
-- AcademiNet - Índices Estratégicos
-- ============================================================

-- ============================================================
-- PRUEBA "SIN ÍNDICES" (BLOQUE DESACTIVADO)
-- ============================================================
-- PostgreSQL no dispone de DISABLE INDEX. Para obtener el plan base,
-- selecciona y ejecuta manualmente SOLO las líneas DROP de este bloque.
-- Después ejecuta ANALYZE y las consultas A/B/C. Para restaurar los índices,
-- vuelve a ejecutar los CREATE INDEX activos de este archivo.
-- Para mediciones estables puedes ejecutar en la sesión:
-- SET max_parallel_workers_per_gather = 0;
--
-- Este bloque NO elimina índices de PRIMARY KEY ni restricciones UNIQUE.
-- Al permanecer comentado, no afecta la inicialización normal de AcademiNet.
--
-- DROP INDEX IF EXISTS idx_pub_autor;
-- DROP INDEX IF EXISTS idx_pub_fecha;
-- DROP INDEX IF EXISTS idx_pub_autor_estado;
-- DROP INDEX IF EXISTS idx_pub_tipo;
-- DROP INDEX IF EXISTS idx_pub_id_foto;
--
-- DROP INDEX IF EXISTS idx_com_publicacion;
-- DROP INDEX IF EXISTS idx_com_pub_fecha;
-- DROP INDEX IF EXISTS idx_com_usuario;
--
-- DROP INDEX IF EXISTS idx_foto_usuario;
-- DROP INDEX IF EXISTS idx_likes_pub_pub;
-- DROP INDEX IF EXISTS idx_likes_pub_usr;
--
-- DROP INDEX IF EXISTS idx_usr_cargo;
-- DROP INDEX IF EXISTS idx_usr_email;
--
-- DROP INDEX IF EXISTS idx_tc_origen;
-- DROP INDEX IF EXISTS idx_tc_destino;
--
-- ANALYZE usuarios;
-- ANALYZE publicaciones;
-- ANALYZE fotografias;
-- ANALYZE comentarios;
-- ANALYZE likes_publicaciones;
-- ANALYZE transferencias_creditos;

-- ============================================================
-- ÍNDICES ACTIVOS (RESTAURACIÓN / ARRANQUE NORMAL)
-- ============================================================

-- publicaciones
CREATE INDEX IF NOT EXISTS idx_pub_autor        ON publicaciones (autor);
CREATE INDEX IF NOT EXISTS idx_pub_fecha        ON publicaciones (fecha_publicacion DESC);
CREATE INDEX IF NOT EXISTS idx_pub_autor_estado ON publicaciones (autor, estado) WHERE estado = 'activo';
CREATE INDEX IF NOT EXISTS idx_pub_tipo         ON publicaciones (tipo);
CREATE INDEX IF NOT EXISTS idx_pub_id_foto      ON publicaciones (id_foto) WHERE id_foto IS NOT NULL;

-- comentarios
CREATE INDEX IF NOT EXISTS idx_com_publicacion  ON comentarios (id_publicacion);
CREATE INDEX IF NOT EXISTS idx_com_pub_fecha    ON comentarios (id_publicacion, fecha_comentario DESC);
CREATE INDEX IF NOT EXISTS idx_com_usuario      ON comentarios (id_usuario);

-- fotografias
CREATE INDEX IF NOT EXISTS idx_foto_usuario     ON fotografias (id_usuario);

-- likes_publicaciones
CREATE INDEX IF NOT EXISTS idx_likes_pub_pub    ON likes_publicaciones (id_publicacion);
CREATE INDEX IF NOT EXISTS idx_likes_pub_usr    ON likes_publicaciones (id_usuario);

-- usuarios
CREATE INDEX IF NOT EXISTS idx_usr_cargo        ON usuarios (cargo);
CREATE INDEX IF NOT EXISTS idx_usr_email        ON usuarios (email);

-- transferencias_creditos
CREATE INDEX IF NOT EXISTS idx_tc_origen        ON transferencias_creditos (id_usuario_origen);
CREATE INDEX IF NOT EXISTS idx_tc_destino       ON transferencias_creditos (id_usuario_destino);

-- ============================================================
-- CONSULTAS DIAGNÓSTICO — ejecutar con EXPLAIN ANALYZE
-- antes y después de crear los índices para medir mejora.
-- ============================================================

-- CONSULTA A
-- EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
-- SELECT u.id_usuario, u.nombres, u.apellidos, u.cargo, COUNT(p.id) AS total_pubs
-- FROM usuarios u
-- JOIN publicaciones p ON p.autor = u.id_usuario AND p.estado = 'activo'
-- GROUP BY u.id_usuario, u.nombres, u.apellidos, u.cargo
-- HAVING COUNT(p.id) > 10
-- ORDER BY total_pubs DESC;

-- CONSULTA B
-- EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
-- SELECT u.id_usuario, u.nombres, u.apellidos,
--        COUNT(DISTINCT p.id_foto) AS total_fotos,
--        COUNT(DISTINCT c.id_comentario) AS total_comentarios
-- FROM usuarios u
-- JOIN publicaciones p ON p.autor = u.id_usuario AND p.estado = 'activo' AND p.id_foto IS NOT NULL
-- JOIN comentarios c ON c.id_publicacion = p.id
--      AND c.fecha_comentario >= NOW() - INTERVAL '1 month'
-- GROUP BY u.id_usuario, u.nombres, u.apellidos
-- HAVING COUNT(DISTINCT c.id_comentario) > 50
-- ORDER BY total_fotos DESC LIMIT 10;

-- CONSULTA C
-- EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
-- WITH likes AS (
--     SELECT id_publicacion, COUNT(*) AS total_likes
--     FROM likes_publicaciones GROUP BY id_publicacion
-- ), comentarios_agrupados AS (
--     SELECT id_publicacion, COUNT(*) AS total_comentarios
--     FROM comentarios GROUP BY id_publicacion
-- )
-- SELECT p.id, p.titulo, (u.nombres||' '||u.apellidos) AS autor,
--        f.id_foto,
--        COALESCE(l.total_likes,0) + COALESCE(c.total_comentarios,0) AS total_interacciones
-- FROM publicaciones p
-- JOIN fotografias f ON f.id_foto = p.id_foto
-- JOIN usuarios u ON u.id_usuario = p.autor
-- LEFT JOIN likes l ON l.id_publicacion = p.id
-- LEFT JOIN comentarios_agrupados c ON c.id_publicacion = p.id
-- WHERE p.estado = 'activo'
-- ORDER BY total_interacciones DESC LIMIT 20;
