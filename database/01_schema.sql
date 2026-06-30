-- ============================================================
-- AcademiNet - Schema de Base de Datos
-- PostgreSQL 17
-- ============================================================

-- ============================================================
-- TABLA: usuarios
-- ============================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario   SERIAL PRIMARY KEY,
    cedula       VARCHAR(13)  NOT NULL UNIQUE,
    apellidos    VARCHAR(100) NOT NULL,
    nombres      VARCHAR(100) NOT NULL,
    cargo        VARCHAR(15)  NOT NULL CHECK (cargo IN ('profesor', 'investigador')),
    email        VARCHAR(150) UNIQUE,
    fecha_nac    DATE,
    created_at   TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- TABLA: cuentas
-- ============================================================
CREATE TABLE IF NOT EXISTS cuentas (
    id_cuenta         SERIAL PRIMARY KEY,
    id_usuario        INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    tipo              VARCHAR(10) NOT NULL DEFAULT 'regular' CHECK (tipo IN ('regular', 'premium')),
    fecha_creacion    TIMESTAMP  NOT NULL DEFAULT NOW(),
    numero_seguidores INT        NOT NULL DEFAULT 0 CHECK (numero_seguidores >= 0),
    privacidad        VARCHAR(10) NOT NULL DEFAULT 'publico' CHECK (privacidad IN ('publico', 'privado')),
    estado            VARCHAR(10) NOT NULL DEFAULT 'activo'  CHECK (estado IN ('activo', 'inactivo')),
    foto_perfil       VARCHAR(500),
    bio               TEXT,
    creditos          INT        NOT NULL DEFAULT 0 CHECK (creditos >= 0)
);

-- ============================================================
-- TABLA: fotografias
-- Almacena la URL (raw GitHub) de la imagen y metadatos.
-- Una fotografía puede estar adjunta a una publicación (relación
-- definida en publicaciones.id_foto).
-- ============================================================
CREATE TABLE IF NOT EXISTS fotografias (
    id_foto      SERIAL PRIMARY KEY,
    id_usuario   INT          NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    ruta_imagen  VARCHAR(500) NOT NULL,
    descripcion  TEXT,
    fecha_subida TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- TABLA: publicaciones
-- Una publicación puede tener opcionalmente una fotografía adjunta.
-- ============================================================
CREATE TABLE IF NOT EXISTS publicaciones (
    id                SERIAL PRIMARY KEY,
    titulo            VARCHAR(255) NOT NULL,
    tipo              VARCHAR(20)  NOT NULL CHECK (tipo IN ('paper', 'microblog', 'comentario')),
    autor             INT          NOT NULL REFERENCES usuarios(id_usuario)   ON DELETE CASCADE ON UPDATE CASCADE,
    id_foto           INT                   REFERENCES fotografias(id_foto)   ON DELETE SET NULL ON UPDATE CASCADE,
    fecha_publicacion TIMESTAMP    NOT NULL DEFAULT NOW() CHECK (fecha_publicacion <= NOW()),
    nro_citaciones    INT          NOT NULL DEFAULT 0 CHECK (nro_citaciones >= 0),
    contenido         TEXT,
    estado            VARCHAR(10)  NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo', 'eliminado'))
);

-- ============================================================
-- TABLA INTERMEDIA: comentarios (sobre publicaciones)
-- ============================================================
CREATE TABLE IF NOT EXISTS comentarios (
    id_comentario    SERIAL PRIMARY KEY,
    id_publicacion   INT  NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE ON UPDATE CASCADE,
    id_usuario       INT  NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    contenido        TEXT NOT NULL,
    fecha_comentario TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- TABLA INTERMEDIA: likes_publicaciones
-- ============================================================
CREATE TABLE IF NOT EXISTS likes_publicaciones (
    id_like        SERIAL PRIMARY KEY,
    id_publicacion INT NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE ON UPDATE CASCADE,
    id_usuario     INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    fecha_like     TIMESTAMP DEFAULT NOW(),
    UNIQUE (id_publicacion, id_usuario)
);

-- ============================================================
-- TABLA INTERMEDIA: seguidores
-- ============================================================
CREATE TABLE IF NOT EXISTS seguidores (
    id_seguidor  INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    id_seguido   INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    fecha_follow TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (id_seguidor, id_seguido),
    CHECK (id_seguidor <> id_seguido)
);

-- ============================================================
-- TABLA INTERMEDIA: citaciones (entre publicaciones)
-- ============================================================
CREATE TABLE IF NOT EXISTS citaciones (
    id_citacion        SERIAL PRIMARY KEY,
    id_publicacion_src INT NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE ON UPDATE CASCADE,
    id_publicacion_dst INT NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE ON UPDATE CASCADE,
    id_usuario         INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    fecha_citacion     TIMESTAMP DEFAULT NOW(),
    UNIQUE (id_publicacion_src, id_publicacion_dst)
);

-- ============================================================
-- TABLA: transferencias_creditos (sistema ACID de puntos)
-- ============================================================
CREATE TABLE IF NOT EXISTS transferencias_creditos (
    id_transferencia   SERIAL PRIMARY KEY,
    id_usuario_origen  INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    id_usuario_destino INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    monto              INT NOT NULL CHECK (monto > 0),
    tipo_accion        VARCHAR(20) NOT NULL CHECK (tipo_accion IN ('like', 'citacion')),
    id_referencia      INT,
    fecha              TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- TABLA: auditoria
-- ============================================================
CREATE TABLE IF NOT EXISTS auditoria (
    id_auditoria     SERIAL PRIMARY KEY,
    tabla_afectada   VARCHAR(50) NOT NULL,
    operacion        VARCHAR(20) NOT NULL,
    id_usuario       INT,
    descripcion      TEXT,
    datos_anteriores JSONB,
    datos_nuevos     JSONB,
    fecha_evento     TIMESTAMP DEFAULT NOW()
);
