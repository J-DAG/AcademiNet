-- ============================================================
-- AcademiNet - Schema de Base de Datos
-- PostgreSQL 17
-- ============================================================

-- ============================================================
-- TABLA: usuarios
-- ============================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario   SERIAL PRIMARY KEY,
    cedula       VARCHAR(13)  NOT NULL UNIQUE CHECK (cedula ~ '^[0-9]{10,13}$'),
    apellidos    VARCHAR(100) NOT NULL CHECK (btrim(apellidos) <> ''),
    nombres      VARCHAR(100) NOT NULL CHECK (btrim(nombres) <> ''),
    cargo        VARCHAR(15)  NOT NULL CHECK (cargo IN ('profesor', 'investigador')),
    email        VARCHAR(150) UNIQUE,
    fecha_nac    DATE CHECK (fecha_nac IS NULL OR fecha_nac <= CURRENT_DATE),
    created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLA: cuentas
-- ============================================================
CREATE TABLE IF NOT EXISTS cuentas (
    id_cuenta         SERIAL PRIMARY KEY,
    id_usuario        INT NOT NULL UNIQUE REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    tipo              VARCHAR(10) NOT NULL DEFAULT 'regular' CHECK (tipo IN ('regular', 'premium')),
    fecha_creacion    TIMESTAMP  NOT NULL DEFAULT NOW(),
    numero_seguidores INT        NOT NULL DEFAULT 0 CHECK (numero_seguidores >= 0),
    privacidad        VARCHAR(10) NOT NULL DEFAULT 'publico' CHECK (privacidad IN ('publico', 'privado')),
    estado            VARCHAR(10) NOT NULL DEFAULT 'activo'  CHECK (estado IN ('activo', 'inactivo')),
    bio               TEXT,
    creditos          INT        NOT NULL DEFAULT 100 CHECK (creditos >= 0)
);

-- ============================================================
-- TABLA: fotografias
-- Almacena la imagen como BYTEA y sus metadatos.
-- Una fotografía puede estar adjunta a una publicación (relación
-- definida en publicaciones.id_foto).
-- ============================================================
CREATE TABLE IF NOT EXISTS fotografias (
    id_foto      SERIAL PRIMARY KEY,
    id_usuario   INT          NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    objeto       BYTEA NOT NULL CHECK (octet_length(objeto) > 0),
    miniatura    BYTEA,
    nombre_archivo      VARCHAR(255) NOT NULL CHECK (btrim(nombre_archivo) <> ''),
    tipo_mime           VARCHAR(100) NOT NULL CHECK (tipo_mime IN ('image/jpeg', 'image/png', 'image/webp')),
    tipo_mime_miniatura VARCHAR(100),
    tamano_bytes        BIGINT NOT NULL CHECK (tamano_bytes > 0),
    hash_sha256         CHAR(64) NOT NULL UNIQUE CHECK (hash_sha256 ~ '^[0-9a-f]{64}$'),
    descripcion         TEXT,
    fecha_subida        TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLA: publicaciones
-- Una publicación puede tener opcionalmente una fotografía adjunta.
-- ============================================================
CREATE TABLE IF NOT EXISTS publicaciones (
    id                SERIAL PRIMARY KEY,
    titulo            VARCHAR(255) NOT NULL CHECK (btrim(titulo) <> ''),
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
    contenido        TEXT NOT NULL CHECK (btrim(contenido) <> ''),
    fecha_comentario TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLA INTERMEDIA: likes_publicaciones
-- ============================================================
CREATE TABLE IF NOT EXISTS likes_publicaciones (
    id_like        SERIAL PRIMARY KEY,
    id_publicacion INT NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE ON UPDATE CASCADE,
    id_usuario     INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    fecha_like     TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (id_publicacion, id_usuario)
);

-- ============================================================
-- TABLA INTERMEDIA: seguidores
-- ============================================================
CREATE TABLE IF NOT EXISTS seguidores (
    id_seguidor  INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    id_seguido   INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    fecha_follow TIMESTAMP NOT NULL DEFAULT NOW(),
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
    fecha_citacion     TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (id_publicacion_src, id_publicacion_dst),
    CHECK (id_publicacion_src <> id_publicacion_dst)
);

-- ============================================================
-- TABLA: transferencias_creditos (sistema ACID de puntos)
-- ============================================================
CREATE TABLE IF NOT EXISTS transferencias_creditos (
    id_transferencia   SERIAL PRIMARY KEY,
    id_usuario_origen  INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    id_usuario_destino INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    monto              INT NOT NULL CHECK (monto > 0),
    tipo_accion        VARCHAR(20) NOT NULL CHECK (tipo_accion IN ('like', 'citacion', 'demo')),
    id_referencia      INT,
    fecha              TIMESTAMP NOT NULL DEFAULT NOW(),
    CHECK (id_usuario_origen <> id_usuario_destino)
);

-- ============================================================
-- TABLA: auditoria
-- ============================================================
CREATE TABLE IF NOT EXISTS auditoria (
    id_auditoria     SERIAL PRIMARY KEY,
    tabla_afectada   VARCHAR(50) NOT NULL,
    operacion        VARCHAR(40) NOT NULL,
    id_usuario       INT,
    descripcion      TEXT,
    datos_anteriores JSONB,
    datos_nuevos     JSONB,
    fecha_evento     TIMESTAMP NOT NULL DEFAULT NOW()
);
