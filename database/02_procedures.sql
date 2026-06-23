-- ============================================================
-- AcademiNet - Procedimientos y Funciones PL/pgSQL
-- ============================================================

-- ============================================================
-- FUNCIÓN: registrar_usuario_y_cuenta
-- Crea un usuario y su cuenta simultáneamente.
-- Captura excepción por cédula duplicada.
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
    -- Insertar usuario
    INSERT INTO usuarios (cedula, apellidos, nombres, cargo, email)
    VALUES (p_cedula, p_apellidos, p_nombres, p_cargo, p_email)
    RETURNING id_usuario INTO v_id_usuario;

    -- Insertar cuenta asociada
    INSERT INTO cuentas (id_usuario, tipo, privacidad)
    VALUES (v_id_usuario, p_tipo_cuenta, p_privacidad)
    RETURNING id_cuenta INTO v_id_cuenta;

    RETURN jsonb_build_object(
        'success', true,
        'id_usuario', v_id_usuario,
        'id_cuenta', v_id_cuenta,
        'mensaje', 'Usuario y cuenta creados exitosamente'
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
            'mensaje', 'Error: Valor no permitido. Verifique cargo (' || p_cargo || ') o tipo de cuenta (' || p_tipo_cuenta || ').'
        );
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'success', false,
            'mensaje', 'Error inesperado: ' || SQLERRM
        );
END;
$$;


-- ============================================================
-- FUNCIÓN: dar_like_publicacion
-- Transfiere 1 crédito del usuario que da like al autor.
-- Envuelto en transacción ACID (BEGIN..COMMIT/ROLLBACK implícito).
-- ============================================================
CREATE OR REPLACE FUNCTION dar_like_publicacion(
    p_id_usuario     INT,
    p_id_publicacion INT
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_autor         INT;
    v_creditos_orig INT;
BEGIN
    -- Obtener el autor de la publicación
    SELECT autor INTO v_autor
    FROM publicaciones
    WHERE id = p_id_publicacion AND estado = 'activo';

    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Publicación no encontrada o eliminada.');
    END IF;

    IF v_autor = p_id_usuario THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'No puedes dar like a tu propia publicación.');
    END IF;

    -- Evitar doble like
    IF EXISTS (
        SELECT 1 FROM likes_publicaciones
        WHERE id_publicacion = p_id_publicacion AND id_usuario = p_id_usuario
    ) THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Ya diste like a esta publicación.');
    END IF;

    -- Registrar el like
    INSERT INTO likes_publicaciones (id_publicacion, id_usuario)
    VALUES (p_id_publicacion, p_id_usuario);

    -- Transferir 1 crédito al autor (operación ACID)
    UPDATE cuentas SET creditos = creditos + 1 WHERE id_usuario = v_autor;

    -- Registrar la transferencia
    INSERT INTO transferencias_creditos (id_usuario_origen, id_usuario_destino, monto, tipo_accion, id_referencia)
    VALUES (p_id_usuario, v_autor, 1, 'like', p_id_publicacion);

    RETURN jsonb_build_object(
        'success', true,
        'mensaje', 'Like registrado y crédito transferido al autor.'
    );

EXCEPTION
    WHEN OTHERS THEN
        RAISE; -- Re-lanzar para que el bloque transaccional externo haga ROLLBACK
END;
$$;


-- ============================================================
-- FUNCIÓN: citar_publicacion
-- Registra una citación y transfiere 2 créditos al autor citado.
-- ============================================================
CREATE OR REPLACE FUNCTION citar_publicacion(
    p_id_usuario     INT,
    p_pub_origen     INT,  -- publicación del usuario que cita
    p_pub_destino    INT   -- publicación que se está citando
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_autor_citado INT;
BEGIN
    SELECT autor INTO v_autor_citado
    FROM publicaciones
    WHERE id = p_pub_destino AND estado = 'activo';

    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'Publicación citada no encontrada.');
    END IF;

    -- Evitar auto-citación
    IF v_autor_citado = p_id_usuario THEN
        RETURN jsonb_build_object('success', false, 'mensaje', 'No puedes citar tu propia publicación.');
    END IF;

    -- Registrar citación
    INSERT INTO citaciones (id_publicacion_src, id_publicacion_dst, id_usuario)
    VALUES (p_pub_origen, p_pub_destino, p_id_usuario)
    ON CONFLICT (id_publicacion_src, id_publicacion_dst) DO NOTHING;

    -- Incrementar contador de citaciones
    UPDATE publicaciones SET nro_citaciones = nro_citaciones + 1 WHERE id = p_pub_destino;

    -- Transferir 2 créditos al autor citado
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
-- FUNCIÓN: eliminar_publicacion (soft delete con auditoría)
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

    -- Soft delete (el trigger de auditoría lo registra)
    UPDATE publicaciones SET estado = 'eliminado' WHERE id = p_id_publicacion;

    RETURN jsonb_build_object('success', true, 'mensaje', 'Publicación eliminada correctamente.');
END;
$$;


-- ============================================================
-- FUNCIÓN: simular_fallo_creditos (demuestra ROLLBACK)
-- Simula un fallo a mitad de la transferencia de créditos.
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
    -- Paso 1: Descontar créditos del origen
    UPDATE cuentas SET creditos = creditos - p_monto WHERE id_usuario = p_id_usuario_origen;

    -- Simular fallo en medio de la transacción
    IF p_forzar_fallo THEN
        RAISE EXCEPTION 'Fallo simulado a mitad de la transacción (para demostrar ROLLBACK)';
    END IF;

    -- Paso 2: Acreditar al destino (no se ejecuta si hay fallo arriba)
    UPDATE cuentas SET creditos = creditos + p_monto WHERE id_usuario = p_id_usuario_destino;

    INSERT INTO transferencias_creditos (id_usuario_origen, id_usuario_destino, monto, tipo_accion)
    VALUES (p_id_usuario_origen, p_id_usuario_destino, p_monto, 'like');

    RETURN jsonb_build_object('success', true, 'mensaje', 'Transferencia completada.');

EXCEPTION
    WHEN OTHERS THEN
        -- El RAISE dentro del bloque PL/pgSQL hace ROLLBACK implícito de este bloque
        RETURN jsonb_build_object('success', false, 'mensaje', SQLERRM);
END;
$$;


-- ============================================================
-- FUNCIÓN: consulta_A - Profesores/investigadores con más de 10 publicaciones
-- ============================================================
CREATE OR REPLACE FUNCTION consulta_profesores_activos()
RETURNS TABLE (
    id_usuario   INT,
    nombres      VARCHAR,
    apellidos    VARCHAR,
    cargo        VARCHAR,
    total_pubs   BIGINT
)
LANGUAGE sql
AS $$
    SELECT u.id_usuario, u.nombres, u.apellidos, u.cargo, COUNT(p.id) AS total_pubs
    FROM usuarios u
    JOIN publicaciones p ON p.autor = u.id_usuario AND p.estado = 'activo'
    GROUP BY u.id_usuario, u.nombres, u.apellidos, u.cargo
    HAVING COUNT(p.id) > 10
    ORDER BY total_pubs DESC;
$$;


-- ============================================================
-- FUNCIÓN: consulta_B - Top 10 usuarios con más fotos cuyas publicaciones
--          tienen más de 50 comentarios en el último mes
-- ============================================================
CREATE OR REPLACE FUNCTION consulta_top_fotografos()
RETURNS TABLE (
    id_usuario     INT,
    nombres        VARCHAR,
    apellidos      VARCHAR,
    total_fotos    BIGINT,
    total_comentarios BIGINT
)
LANGUAGE sql
AS $$
    SELECT
        u.id_usuario,
        u.nombres,
        u.apellidos,
        COUNT(DISTINCT f.id_foto) AS total_fotos,
        COUNT(DISTINCT c.id_comentario) AS total_comentarios
    FROM usuarios u
    JOIN fotografias f ON f.id_usuario = u.id_usuario
    JOIN publicaciones p ON p.autor = u.id_usuario AND p.estado = 'activo'
    JOIN comentarios c ON c.id_publicacion = p.id
        AND c.fecha_comentario >= NOW() - INTERVAL '1 month'
    GROUP BY u.id_usuario, u.nombres, u.apellidos
    HAVING COUNT(DISTINCT c.id_comentario) > 50
    ORDER BY total_fotos DESC
    LIMIT 10;
$$;


-- ============================================================
-- FUNCIÓN: consulta_C - Fotografías con más interacciones
-- ============================================================
CREATE OR REPLACE FUNCTION consulta_fotos_mas_interacciones()
RETURNS TABLE (
    id_foto        INT,
    descripcion    TEXT,
    nombre_usuario TEXT,
    likes          INT,
    comentarios    BIGINT,
    total_interacciones BIGINT
)
LANGUAGE sql
AS $$
    SELECT
        f.id_foto,
        f.descripcion,
        (u.nombres || ' ' || u.apellidos)::TEXT AS nombre_usuario,
        f.nro_likes AS likes,
        COUNT(cf.id_comentario) AS comentarios,
        (f.nro_likes + COUNT(cf.id_comentario)) AS total_interacciones
    FROM fotografias f
    JOIN usuarios u ON u.id_usuario = f.id_usuario
    LEFT JOIN comentarios_foto cf ON cf.id_foto = f.id_foto
    GROUP BY f.id_foto, f.descripcion, nombre_usuario, f.nro_likes
    ORDER BY total_interacciones DESC
    LIMIT 20;
$$;
