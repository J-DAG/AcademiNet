-- ============================================================
-- AcademiNet - Reporte Top 10 Fotógrafos
-- ============================================================
-- Criterio:
--   Usuarios con más fotografías adjuntas a publicaciones activas
--   y más de 50 comentarios recibidos durante el último mes.

-- Datos demostrativos idempotentes:
-- selecciona los 10 autores con más fotografías y completa hasta 60 comentarios
-- recientes por autor. Solo agrega lo que haga falta en cada ejecución.
DO $$
DECLARE
    candidato RECORD;
    v_total_recientes INT;
    v_faltantes INT;
    v_comentarista INT;
    i INT;
BEGIN
    FOR candidato IN
        SELECT p.autor, MIN(p.id) AS id_publicacion,
               COUNT(DISTINCT p.id_foto) AS total_fotos
        FROM publicaciones p
        WHERE p.estado = 'activo' AND p.id_foto IS NOT NULL
        GROUP BY p.autor
        ORDER BY total_fotos DESC, p.autor
        LIMIT 10
    LOOP
        SELECT COUNT(DISTINCT c.id_comentario)::INT
        INTO v_total_recientes
        FROM publicaciones p
        LEFT JOIN comentarios c
            ON c.id_publicacion = p.id
           AND c.fecha_comentario >= NOW() - INTERVAL '1 month'
        WHERE p.autor = candidato.autor
          AND p.estado = 'activo'
          AND p.id_foto IS NOT NULL;

        v_faltantes := GREATEST(60 - v_total_recientes, 0);
        IF v_faltantes > 0 THEN
            SELECT id_usuario INTO v_comentarista
            FROM usuarios
            WHERE id_usuario <> candidato.autor
            ORDER BY id_usuario
            LIMIT 1;

            FOR i IN 1..v_faltantes LOOP
                INSERT INTO comentarios
                    (id_publicacion, id_usuario, contenido, fecha_comentario)
                VALUES (
                    candidato.id_publicacion,
                    v_comentarista,
                    format('[DEMO_TOP_FOTOGRAFOS] Comentario académico %s para autor #%s',
                           v_total_recientes + i, candidato.autor),
                    NOW() - ((i % 20) || ' minutes')::INTERVAL
                );
            END LOOP;
        END IF;
    END LOOP;
END;
$$;

CREATE OR REPLACE VIEW vw_top_fotografos AS
SELECT
    u.id_usuario,
    u.nombres,
    u.apellidos,
    COUNT(DISTINCT p.id_foto)       AS total_fotos,
    COUNT(DISTINCT p.id)            AS publicaciones_con_foto,
    COUNT(DISTINCT c.id_comentario) AS comentarios_ultimo_mes
FROM usuarios u
JOIN publicaciones p
    ON p.autor = u.id_usuario
   AND p.estado = 'activo'
   AND p.id_foto IS NOT NULL
JOIN comentarios c
    ON c.id_publicacion = p.id
   AND c.fecha_comentario >= NOW() - INTERVAL '1 month'
GROUP BY u.id_usuario, u.nombres, u.apellidos
HAVING COUNT(DISTINCT c.id_comentario) > 50;

-- Reporte final solicitado.
SELECT
    id_usuario,
    nombres,
    apellidos,
    total_fotos,
    publicaciones_con_foto,
    comentarios_ultimo_mes
FROM vw_top_fotografos
ORDER BY total_fotos DESC, comentarios_ultimo_mes DESC
LIMIT 10;
