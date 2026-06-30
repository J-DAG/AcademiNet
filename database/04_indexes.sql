-- ============================================================
-- AcademiNet - Índices Estratégicos
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
-- EXPLAIN ANALYZE
-- SELECT u.id_usuario, u.nombres, u.apellidos, u.cargo, COUNT(p.id) AS total_pubs
-- FROM usuarios u
-- JOIN publicaciones p ON p.autor = u.id_usuario AND p.estado = 'activo'
-- GROUP BY u.id_usuario, u.nombres, u.apellidos, u.cargo
-- HAVING COUNT(p.id) > 10
-- ORDER BY total_pubs DESC;

-- CONSULTA B
-- EXPLAIN ANALYZE
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
-- EXPLAIN ANALYZE
-- SELECT p.id, p.titulo, (u.nombres||' '||u.apellidos) AS autor,
--        f.ruta_imagen,
--        COUNT(DISTINCT lp.id_like) + COUNT(DISTINCT c.id_comentario) AS total_interacciones
-- FROM publicaciones p
-- JOIN fotografias f ON f.id_foto = p.id_foto
-- JOIN usuarios u ON u.id_usuario = p.autor
-- LEFT JOIN likes_publicaciones lp ON lp.id_publicacion = p.id
-- LEFT JOIN comentarios c ON c.id_publicacion = p.id
-- WHERE p.estado = 'activo'
-- GROUP BY p.id, p.titulo, autor, f.ruta_imagen
-- ORDER BY total_interacciones DESC LIMIT 20;
