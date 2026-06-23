-- ============================================================
-- AcademiNet - Triggers de Auditoría y Control de Negocio
-- ============================================================

-- ============================================================
-- TRIGGER 1: Auditoría de cambio de foto de perfil
-- Registra en auditoría cuando se actualiza foto_perfil en cuentas.
-- ============================================================
CREATE OR REPLACE FUNCTION fn_auditoria_foto_perfil()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.foto_perfil IS DISTINCT FROM NEW.foto_perfil THEN
        INSERT INTO auditoria (tabla_afectada, operacion, id_usuario, descripcion, datos_anteriores, datos_nuevos)
        VALUES (
            'cuentas',
            'UPDATE_FOTO_PERFIL',
            NEW.id_usuario,
            'El usuario cambió su foto de perfil',
            jsonb_build_object('foto_perfil', 'BYTEA_ANTERIOR', 'updated_at', NOW()),
            jsonb_build_object('foto_perfil', 'BYTEA_NUEVA',    'updated_at', NOW())
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_auditoria_foto_perfil ON cuentas;
CREATE TRIGGER trg_auditoria_foto_perfil
    AFTER UPDATE ON cuentas
    FOR EACH ROW
    EXECUTE FUNCTION fn_auditoria_foto_perfil();


-- ============================================================
-- TRIGGER 2: Auditoría de eliminación de publicación
-- Registra en auditoría cuando una publicación cambia a estado 'eliminado'.
-- ============================================================
CREATE OR REPLACE FUNCTION fn_auditoria_eliminacion_publicacion()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.estado = 'activo' AND NEW.estado = 'eliminado' THEN
        INSERT INTO auditoria (tabla_afectada, operacion, id_usuario, descripcion, datos_anteriores, datos_nuevos)
        VALUES (
            'publicaciones',
            'DELETE',
            OLD.autor,
            'El usuario eliminó la publicación: ' || OLD.titulo,
            jsonb_build_object(
                'id', OLD.id,
                'titulo', OLD.titulo,
                'tipo', OLD.tipo,
                'fecha_publicacion', OLD.fecha_publicacion
            ),
            jsonb_build_object('estado', 'eliminado', 'fecha_eliminacion', NOW())
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_auditoria_eliminacion ON publicaciones;
CREATE TRIGGER trg_auditoria_eliminacion
    AFTER UPDATE ON publicaciones
    FOR EACH ROW
    EXECUTE FUNCTION fn_auditoria_eliminacion_publicacion();


-- ============================================================
-- TRIGGER 3: Anti-spam de publicaciones
-- Impide publicar más de 5 veces en un lapso de 1 minuto.
-- ============================================================
CREATE OR REPLACE FUNCTION fn_antispam_publicaciones()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM publicaciones
    WHERE autor = NEW.autor
      AND fecha_publicacion >= NOW() - INTERVAL '1 minute';

    IF v_count >= 5 THEN
        RAISE EXCEPTION 'ANTISPAM: No puedes publicar más de 5 veces por minuto. Espera antes de publicar de nuevo.';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_antispam_publicaciones ON publicaciones;
CREATE TRIGGER trg_antispam_publicaciones
    BEFORE INSERT ON publicaciones
    FOR EACH ROW
    EXECUTE FUNCTION fn_antispam_publicaciones();


-- ============================================================
-- TRIGGER 4: Actualizar contador de seguidores automáticamente
-- ============================================================
CREATE OR REPLACE FUNCTION fn_actualizar_seguidores()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
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
    FOR EACH ROW
    EXECUTE FUNCTION fn_actualizar_seguidores();


-- ============================================================
-- TRIGGER 5: Actualizar nro_likes en fotografías automáticamente
-- ============================================================
CREATE OR REPLACE FUNCTION fn_actualizar_likes_foto()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE fotografias SET nro_likes = nro_likes + 1 WHERE id_foto = NEW.id_foto;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE fotografias SET nro_likes = GREATEST(nro_likes - 1, 0) WHERE id_foto = OLD.id_foto;
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$;

DROP TRIGGER IF EXISTS trg_actualizar_likes_foto ON likes_fotografias;
CREATE TRIGGER trg_actualizar_likes_foto
    AFTER INSERT OR DELETE ON likes_fotografias
    FOR EACH ROW
    EXECUTE FUNCTION fn_actualizar_likes_foto();
