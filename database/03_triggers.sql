-- ============================================================
-- AcademiNet - Triggers de Auditoría y Control de Negocio
-- ============================================================

DROP TRIGGER IF EXISTS trg_auditoria_foto_perfil ON cuentas;
DROP FUNCTION IF EXISTS fn_auditoria_foto_perfil();


-- ============================================================
-- TRIGGER 2: Auditoría de eliminación de publicación
-- ============================================================
CREATE OR REPLACE FUNCTION fn_auditoria_eliminacion_publicacion()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.estado = 'activo' AND NEW.estado = 'eliminado' THEN
        INSERT INTO auditoria (tabla_afectada, operacion, id_usuario, descripcion, datos_anteriores, datos_nuevos)
        VALUES (
            'publicaciones', 'DELETE', OLD.autor,
            'El usuario eliminó la publicación: ' || OLD.titulo,
            jsonb_build_object('id', OLD.id, 'titulo', OLD.titulo, 'tipo', OLD.tipo,
                               'fecha_publicacion', OLD.fecha_publicacion, 'id_foto', OLD.id_foto),
            jsonb_build_object('estado', 'eliminado', 'fecha_eliminacion', NOW())
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_auditoria_eliminacion ON publicaciones;
CREATE TRIGGER trg_auditoria_eliminacion
    AFTER UPDATE ON publicaciones
    FOR EACH ROW EXECUTE FUNCTION fn_auditoria_eliminacion_publicacion();


-- ============================================================
-- Auditoría de transferencias de créditos confirmadas
-- ============================================================
CREATE OR REPLACE FUNCTION fn_auditoria_transferencia_creditos()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO auditoria
        (tabla_afectada, operacion, id_usuario, descripcion, datos_nuevos)
    VALUES (
        'transferencias_creditos', 'TRANSFERENCIA_CREDITOS', NEW.id_usuario_origen,
        format('Usuario #%s transfirió %s créditos al usuario #%s (%s)',
               NEW.id_usuario_origen, NEW.monto, NEW.id_usuario_destino, NEW.tipo_accion),
        jsonb_build_object(
            'id_transferencia', NEW.id_transferencia,
            'origen', NEW.id_usuario_origen,
            'destino', NEW.id_usuario_destino,
            'monto', NEW.monto,
            'tipo_accion', NEW.tipo_accion,
            'id_referencia', NEW.id_referencia
        )
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_auditoria_transferencia_creditos ON transferencias_creditos;
CREATE TRIGGER trg_auditoria_transferencia_creditos
    AFTER INSERT ON transferencias_creditos
    FOR EACH ROW EXECUTE FUNCTION fn_auditoria_transferencia_creditos();


-- ============================================================
-- Auditoría de fotografías registradas (sin duplicar el BYTEA)
-- ============================================================
CREATE OR REPLACE FUNCTION fn_auditoria_registro_fotografia()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO auditoria
        (tabla_afectada, operacion, id_usuario, descripcion, datos_nuevos)
    VALUES (
        'fotografias', 'FOTOGRAFIA_REGISTRADA', NEW.id_usuario,
        format('Usuario #%s registró la fotografía #%s (%s)',
               NEW.id_usuario, NEW.id_foto, COALESCE(NEW.nombre_archivo, 'sin nombre')),
        jsonb_build_object(
            'id_foto', NEW.id_foto,
            'nombre_archivo', NEW.nombre_archivo,
            'tipo_mime', NEW.tipo_mime,
            'tamano_bytes', NEW.tamano_bytes
        )
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_auditoria_registro_fotografia ON fotografias;
CREATE TRIGGER trg_auditoria_registro_fotografia
    AFTER INSERT ON fotografias
    FOR EACH ROW EXECUTE FUNCTION fn_auditoria_registro_fotografia();


-- ============================================================
-- TRIGGER 3: Anti-spam — máximo 5 publicaciones por minuto
-- ============================================================
CREATE OR REPLACE FUNCTION fn_antispam_publicaciones()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM publicaciones
    WHERE autor = NEW.autor
      AND fecha_publicacion >= NOW() - INTERVAL '1 minute';

    IF v_count >= 5 THEN
        RAISE EXCEPTION 'ANTISPAM: No puedes publicar más de 5 veces por minuto.';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_antispam_publicaciones ON publicaciones;
CREATE TRIGGER trg_antispam_publicaciones
    BEFORE INSERT ON publicaciones
    FOR EACH ROW EXECUTE FUNCTION fn_antispam_publicaciones();


-- ============================================================
-- TRIGGER 4: Actualizar contador de seguidores automáticamente
-- ============================================================
CREATE OR REPLACE FUNCTION fn_actualizar_seguidores()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE cuentas SET numero_seguidores = numero_seguidores + 1
        WHERE id_usuario = NEW.id_seguido;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE cuentas SET numero_seguidores = GREATEST(numero_seguidores - 1, 0)
        WHERE id_usuario = OLD.id_seguido;
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$;

DROP TRIGGER IF EXISTS trg_actualizar_seguidores ON seguidores;
CREATE TRIGGER trg_actualizar_seguidores
    AFTER INSERT OR DELETE ON seguidores
    FOR EACH ROW EXECUTE FUNCTION fn_actualizar_seguidores();

-- Mantiene fotografias.nro_likes consistente con la tabla intermedia.
CREATE OR REPLACE FUNCTION fn_actualizar_likes_fotografia()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE fotografias SET nro_likes = nro_likes + 1 WHERE id_foto = NEW.id_foto;
    ELSE
        UPDATE fotografias SET nro_likes = GREATEST(nro_likes - 1, 0) WHERE id_foto = OLD.id_foto;
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$;

DROP TRIGGER IF EXISTS trg_actualizar_likes_fotografia ON likes_fotografias;
CREATE TRIGGER trg_actualizar_likes_fotografia
    AFTER INSERT OR DELETE ON likes_fotografias
    FOR EACH ROW EXECUTE FUNCTION fn_actualizar_likes_fotografia();
