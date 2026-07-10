-- ============================================================
-- AcademiNet - Procedimientos y Funciones PL/pgSQL
-- ============================================================

-- ============================================================
-- FUNCIÓN: registrar_usuario_y_cuenta
-- ============================================================
CREATE OR REPLACE FUNCTION registrar_usuario_y_cuenta(
    p_cedula       VARCHAR,
    p_apellidos    VARCHAR,
    p_nombres      VARCHAR,
    p_cargo        VARCHAR,
    p_email        VARCHAR,
    p_tipo_cuenta  VARCHAR DEFAULT 'regular',
    p_privacidad   VARCHAR DEFAULT 'publico'
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_id_usuario INT;
    v_id_cuenta  INT;
BEGIN
    INSERT INTO usuarios (cedula, apellidos, nombres, cargo, email)
    VALUES (p_cedula, p_apellidos, p_nombres, p_cargo, p_email)
    RETURNING id_usuario INTO v_id_usuario;

    INSERT INTO cuentas (id_usuario, tipo, privacidad)
    VALUES (v_id_usuario, p_tipo_cuenta, p_privacidad)
    RETURNING id_cuenta INTO v_id_cuenta;

    RETURN jsonb_build_object(
        'success', true,
        'id_usuario', v_id_usuario,
        'id_cuenta',  v_id_cuenta,
        'mensaje',    'Usuario y cuenta creados exitosamente'
    );

EXCEPTION
    WHEN unique_violation THEN
        RETURN jsonb_build_object(
            'success', false,
            'mensaje', 'Error: La cédula ' || p_cedula || ' ya está registrada en el sistema.'
        );
    WHEN check_violation THEN
        RETURN jsonb_build_object(
            'success', false,
            'mensaje', 'Error: Valor no permitido en cargo (' || p_cargo || ') o tipo de cuenta (' || p_tipo_cuenta || ').'
        );
    WHEN OTHERS THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Error inesperado: ' || SQLERRM);
END;
$$;


-- ============================================================
-- FUNCIÓN: dar_like_publicacion
-- Transfiere 1 crédito del usuario que da like al autor (ACID).
-- ============================================================
CREATE OR REPLACE FUNCTION dar_like_publicacion(
    p_id_usuario     INT,
    p_id_publicacion INT
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_autor INT;
    v_creditos INT;
BEGIN
    SELECT autor INTO v_autor
    FROM publicaciones
    WHERE id = p_id_publicacion AND estado = 'activo';

    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Publicación no encontrada o eliminada.');
    END IF;

    IF v_autor = p_id_usuario THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'No puedes dar like a tu propia publicación.');
    END IF;

    IF EXISTS (
        SELECT 1 FROM likes_publicaciones
        WHERE id_publicacion = p_id_publicacion AND id_usuario = p_id_usuario
    ) THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Ya diste like a esta publicación.');
    END IF;

    PERFORM 1 FROM cuentas
    WHERE id_usuario IN (p_id_usuario, v_autor)
    ORDER BY id_usuario FOR UPDATE;

    SELECT creditos INTO v_creditos FROM cuentas WHERE id_usuario = p_id_usuario;
    IF NOT FOUND OR v_creditos < 1 THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Créditos insuficientes para dar like.');
    END IF;

    INSERT INTO likes_publicaciones (id_publicacion, id_usuario)
    VALUES (p_id_publicacion, p_id_usuario);

    UPDATE cuentas SET creditos = creditos - 1 WHERE id_usuario = p_id_usuario;
    UPDATE cuentas SET creditos = creditos + 1 WHERE id_usuario = v_autor;

    INSERT INTO transferencias_creditos (id_usuario_origen, id_usuario_destino, monto, tipo_accion, id_referencia)
    VALUES (p_id_usuario, v_autor, 1, 'like', p_id_publicacion);

    RETURN jsonb_build_object('success', true, 'mensaje', 'Like registrado y 1 crédito transferido al autor.');

EXCEPTION
    WHEN OTHERS THEN
        RAISE;
END;
$$;


-- ============================================================
-- FUNCIÓN: citar_publicacion
-- Transfiere 2 créditos al autor citado (ACID).
-- ============================================================
CREATE OR REPLACE FUNCTION citar_publicacion(
    p_id_usuario  INT,
    p_pub_origen  INT,
    p_pub_destino INT
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_autor_citado INT;
    v_autor_origen INT;
    v_creditos INT;
    v_insertada INT;
BEGIN
    SELECT autor INTO v_autor_citado
    FROM publicaciones
    WHERE id = p_pub_destino AND estado = 'activo';

    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Publicación citada no encontrada.');
    END IF;

    IF v_autor_citado = p_id_usuario THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'No puedes citar tu propia publicación.');
    END IF;

    SELECT autor INTO v_autor_origen FROM publicaciones
    WHERE id = p_pub_origen AND estado = 'activo';
    IF NOT FOUND OR v_autor_origen <> p_id_usuario THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'La publicación de origen no pertenece al usuario o no está activa.');
    END IF;
    IF p_pub_origen = p_pub_destino THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Una publicación no puede citarse a sí misma.');
    END IF;

    PERFORM 1 FROM cuentas
    WHERE id_usuario IN (p_id_usuario, v_autor_citado)
    ORDER BY id_usuario FOR UPDATE;
    SELECT creditos INTO v_creditos FROM cuentas WHERE id_usuario = p_id_usuario;
    IF v_creditos < 2 THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Créditos insuficientes para citar.');
    END IF;

    INSERT INTO citaciones (id_publicacion_src, id_publicacion_dst, id_usuario)
    VALUES (p_pub_origen, p_pub_destino, p_id_usuario)
    ON CONFLICT (id_publicacion_src, id_publicacion_dst) DO NOTHING;

    GET DIAGNOSTICS v_insertada = ROW_COUNT;
    IF v_insertada = 0 THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Esta citación ya existe.');
    END IF;

    UPDATE publicaciones SET nro_citaciones = nro_citaciones + 1 WHERE id = p_pub_destino;

    UPDATE cuentas SET creditos = creditos - 2 WHERE id_usuario = p_id_usuario;
    UPDATE cuentas SET creditos = creditos + 2 WHERE id_usuario = v_autor_citado;

    INSERT INTO transferencias_creditos (id_usuario_origen, id_usuario_destino, monto, tipo_accion, id_referencia)
    VALUES (p_id_usuario, v_autor_citado, 2, 'citacion', p_pub_destino);

    RETURN jsonb_build_object('success', true, 'mensaje', 'Citación registrada y 2 créditos transferidos al autor.');

EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Error: ' || SQLERRM);
END;
$$;


-- ============================================================
-- FUNCIÓN: eliminar_publicacion (soft delete)
-- ============================================================
CREATE OR REPLACE FUNCTION eliminar_publicacion(
    p_id_publicacion INT,
    p_id_usuario     INT
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_autor INT;
BEGIN
    SELECT autor INTO v_autor FROM publicaciones WHERE id = p_id_publicacion;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Publicación no encontrada.');
    END IF;

    IF v_autor <> p_id_usuario THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Solo el autor puede eliminar su publicación.');
    END IF;

    UPDATE publicaciones SET estado = 'eliminado' WHERE id = p_id_publicacion;

    RETURN jsonb_build_object('success', true, 'mensaje', 'Publicación eliminada correctamente.');
END;
$$;


-- ============================================================
-- FUNCIÓN: simular_fallo_creditos (demo ROLLBACK / ACID)
-- ============================================================
CREATE OR REPLACE FUNCTION simular_fallo_creditos(
    p_id_usuario_origen  INT,
    p_id_usuario_destino INT,
    p_monto              INT,
    p_forzar_fallo       BOOLEAN DEFAULT false
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_monto <= 0 OR p_id_usuario_origen = p_id_usuario_destino THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Transferencia inválida.');
    END IF;
    PERFORM 1 FROM cuentas
    WHERE id_usuario IN (p_id_usuario_origen, p_id_usuario_destino)
    ORDER BY id_usuario FOR UPDATE;
    IF COALESCE((SELECT creditos FROM cuentas WHERE id_usuario = p_id_usuario_origen), -1) < p_monto THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Créditos insuficientes.');
    END IF;

    UPDATE cuentas SET creditos = creditos - p_monto WHERE id_usuario = p_id_usuario_origen;

    IF p_forzar_fallo THEN
        RAISE EXCEPTION 'Fallo simulado a mitad de la transacción (para demostrar ROLLBACK)';
    END IF;

    UPDATE cuentas SET creditos = creditos + p_monto WHERE id_usuario = p_id_usuario_destino;

    INSERT INTO transferencias_creditos (id_usuario_origen, id_usuario_destino, monto, tipo_accion)
    VALUES (p_id_usuario_origen, p_id_usuario_destino, p_monto, 'like');

    RETURN jsonb_build_object('success', true, 'mensaje', 'Transferencia completada.');

EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object('success', false, 'mensaje', SQLERRM);
END;
$$;


-- ============================================================
-- CONSULTA A: Profesores/investigadores con más de 10 publicaciones
-- ============================================================
CREATE OR REPLACE FUNCTION consulta_profesores_activos()
RETURNS TABLE (
    id_usuario INT, nombres VARCHAR, apellidos VARCHAR,
    cargo VARCHAR, total_pubs BIGINT
)
LANGUAGE sql AS $$
    SELECT u.id_usuario, u.nombres, u.apellidos, u.cargo, COUNT(p.id) AS total_pubs
    FROM usuarios u
    JOIN publicaciones p ON p.autor = u.id_usuario AND p.estado = 'activo'
    GROUP BY u.id_usuario, u.nombres, u.apellidos, u.cargo
    HAVING COUNT(p.id) > 10
    ORDER BY total_pubs DESC;
$$;


-- ============================================================
-- CONSULTA B: Top 10 usuarios con más fotografías adjuntas en sus
-- publicaciones que recibieron más de 50 comentarios en el último mes
-- ============================================================
CREATE OR REPLACE FUNCTION consulta_top_fotografos()
RETURNS TABLE (
    id_usuario        INT,
    nombres           VARCHAR,
    apellidos         VARCHAR,
    total_fotos       BIGINT,
    total_comentarios BIGINT
)
LANGUAGE sql AS $$
    SELECT
        u.id_usuario,
        u.nombres,
        u.apellidos,
        COUNT(DISTINCT p.id_foto)        AS total_fotos,
        COUNT(DISTINCT c.id_comentario)  AS total_comentarios
    FROM usuarios u
    JOIN publicaciones p ON p.autor = u.id_usuario
                         AND p.estado = 'activo'
                         AND p.id_foto IS NOT NULL
    JOIN comentarios c   ON c.id_publicacion = p.id
                         AND c.fecha_comentario >= NOW() - INTERVAL '1 month'
    GROUP BY u.id_usuario, u.nombres, u.apellidos
    HAVING COUNT(DISTINCT c.id_comentario) > 50
    ORDER BY total_fotos DESC
    LIMIT 10;
$$;


-- ============================================================
-- CONSULTA C: Publicaciones con foto ordenadas por interacciones
-- (likes + comentarios). Reemplaza la anterior "fotos con más likes"
-- ya que likes y comentarios ahora pertenecen a la publicación.
-- ============================================================
CREATE OR REPLACE FUNCTION consulta_fotos_mas_interacciones()
RETURNS TABLE (
    id_pub              INT,
    titulo              VARCHAR,
    nombre_autor        TEXT,
    ruta_imagen         VARCHAR,
    descripcion_foto    TEXT,
    nro_likes           BIGINT,
    nro_comentarios     BIGINT,
    total_interacciones BIGINT
)
LANGUAGE sql AS $$
    SELECT
        p.id                                            AS id_pub,
        p.titulo,
        (u.nombres || ' ' || u.apellidos)::TEXT         AS nombre_autor,
        ('/api/fotografias/' || f.id_foto || '/archivo')::VARCHAR AS ruta_imagen,
        f.descripcion                                   AS descripcion_foto,
        COUNT(DISTINCT lp.id_like)                      AS nro_likes,
        COUNT(DISTINCT c.id_comentario)                 AS nro_comentarios,
        COUNT(DISTINCT lp.id_like) + COUNT(DISTINCT c.id_comentario) AS total_interacciones
    FROM publicaciones p
    JOIN fotografias f         ON f.id_foto = p.id_foto
    JOIN usuarios u            ON u.id_usuario = p.autor
    LEFT JOIN likes_publicaciones lp ON lp.id_publicacion = p.id
    LEFT JOIN comentarios c          ON c.id_publicacion  = p.id
    WHERE p.estado = 'activo'
    GROUP BY p.id, p.titulo, nombre_autor, f.id_foto, f.descripcion
    ORDER BY total_interacciones DESC
    LIMIT 20;
$$;
