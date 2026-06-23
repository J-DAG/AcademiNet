-- ============================================================
-- AcademiNet - Índices Estratégicos y Análisis de Optimización
-- ============================================================
-- Ejecutar EXPLAIN ANALYZE antes y después de crear cada índice
-- para medir reducción de costo y tiempo de respuesta.
-- ============================================================

-- ============================================================
-- ÍNDICES EN: publicaciones
-- ============================================================

-- B-Tree sobre autor: aceleran joins y filtros por usuario
CREATE INDEX IF NOT EXISTS idx_pub_autor
    ON publicaciones (autor);

-- B-Tree sobre fecha_publicacion: acelera filtros por rango de fechas
CREATE INDEX IF NOT EXISTS idx_pub_fecha
    ON publicaciones (fecha_publicacion DESC);

-- Índice compuesto (autor + estado): optimiza consulta A
CREATE INDEX IF NOT EXISTS idx_pub_autor_estado
    ON publicaciones (autor, estado)
    WHERE estado = 'activo';

-- Índice sobre tipo: filtros por tipo de publicación
CREATE INDEX IF NOT EXISTS idx_pub_tipo
    ON publicaciones (tipo);


-- ============================================================
-- ÍNDICES EN: comentarios
-- ============================================================

-- B-Tree sobre id_publicacion: acelera COUNT de comentarios por publicación
CREATE INDEX IF NOT EXISTS idx_com_publicacion
    ON comentarios (id_publicacion);

-- Índice compuesto para consulta B (publicación + fecha último mes)
CREATE INDEX IF NOT EXISTS idx_com_pub_fecha
    ON comentarios (id_publicacion, fecha_comentario DESC);

-- Índice sobre id_usuario en comentarios
CREATE INDEX IF NOT EXISTS idx_com_usuario
    ON comentarios (id_usuario);


-- ============================================================
-- ÍNDICES EN: fotografias
-- ============================================================

-- B-Tree sobre id_usuario: acelera consulta B (fotos por usuario)
CREATE INDEX IF NOT EXISTS idx_foto_usuario
    ON fotografias (id_usuario);

-- B-Tree sobre nro_likes: acelera consulta C (ordenar por likes)
CREATE INDEX IF NOT EXISTS idx_foto_likes
    ON fotografias (nro_likes DESC);


-- ============================================================
-- ÍNDICES EN: likes_publicaciones y likes_fotografias
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_likes_pub_pub
    ON likes_publicaciones (id_publicacion);

CREATE INDEX IF NOT EXISTS idx_likes_pub_usr
    ON likes_publicaciones (id_usuario);

CREATE INDEX IF NOT EXISTS idx_likes_foto_foto
    ON likes_fotografias (id_foto);


-- ============================================================
-- ÍNDICES EN: usuarios
-- ============================================================

-- B-Tree sobre cargo: filtros por profesor/investigador
CREATE INDEX IF NOT EXISTS idx_usr_cargo
    ON usuarios (cargo);

-- B-Tree sobre email
CREATE INDEX IF NOT EXISTS idx_usr_email
    ON usuarios (email);


-- ============================================================
-- ÍNDICES EN: transferencias_creditos
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_tc_origen
    ON transferencias_creditos (id_usuario_origen);

CREATE INDEX IF NOT EXISTS idx_tc_destino
    ON transferencias_creditos (id_usuario_destino);


-- ============================================================
-- CONSULTAS DE DIAGNÓSTICO - Ejecutar ANTES y DESPUÉS de índices
-- ============================================================

-- CONSULTA A: Profesores/investigadores con más de 10 publicaciones
-- EXPLAIN ANALYZE
-- SELECT u.id_usuario, u.nombres, u.apellidos, u.cargo, COUNT(p.id) AS total_pubs
-- FROM usuarios u
-- JOIN publicaciones p ON p.autor = u.id_usuario AND p.estado = 'activo'
-- GROUP BY u.id_usuario, u.nombres, u.apellidos, u.cargo
-- HAVING COUNT(p.id) > 10
-- ORDER BY total_pubs DESC;

-- CONSULTA B: Top 10 usuarios con más fotos y >50 comentarios último mes
-- EXPLAIN ANALYZE
-- SELECT u.id_usuario, u.nombres, u.apellidos,
--        COUNT(DISTINCT f.id_foto) AS total_fotos,
--        COUNT(DISTINCT c.id_comentario) AS total_comentarios
-- FROM usuarios u
-- JOIN fotografias f ON f.id_usuario = u.id_usuario
-- JOIN publicaciones p ON p.autor = u.id_usuario AND p.estado = 'activo'
-- JOIN comentarios c ON c.id_publicacion = p.id
--      AND c.fecha_comentario >= NOW() - INTERVAL '1 month'
-- GROUP BY u.id_usuario, u.nombres, u.apellidos
-- HAVING COUNT(DISTINCT c.id_comentario) > 50
-- ORDER BY total_fotos DESC
-- LIMIT 10;

-- CONSULTA C: Fotografías con más interacciones (likes + comentarios)
-- EXPLAIN ANALYZE
-- SELECT f.id_foto, f.descripcion,
--        (u.nombres || ' ' || u.apellidos) AS nombre_usuario,
--        f.nro_likes, COUNT(cf.id_comentario) AS comentarios,
--        (f.nro_likes + COUNT(cf.id_comentario)) AS total_interacciones
-- FROM fotografias f
-- JOIN usuarios u ON u.id_usuario = f.id_usuario
-- LEFT JOIN comentarios_foto cf ON cf.id_foto = f.id_foto
-- GROUP BY f.id_foto, f.descripcion, nombre_usuario, f.nro_likes
-- ORDER BY total_interacciones DESC
-- LIMIT 20;
