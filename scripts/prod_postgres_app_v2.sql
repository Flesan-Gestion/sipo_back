-- =============================================================================
-- SIPO V2 → PostgreSQL (DB_DATABASE_APP / schema app PRODUCCIÓN)
-- Tablas NUEVAS de V2 (fichas, historial, portales). Schema final consolidado.
-- Preferible: apuntar .env a este Postgres y ejecutar:
--   python manage.py migrate
-- Este SQL sirve si quieres crear solo las tablas de negocio a mano.
-- Después igual conviene `migrate` para django_* y django_migrations.
-- =============================================================================

CREATE TABLE IF NOT EXISTS sipo_ficha_ingreso (
    id BIGSERIAL PRIMARY KEY,
    razon_social_id VARCHAR(50) NULL,
    razon_social_nombre VARCHAR(255) NULL,
    obra VARCHAR(255) NULL,
    centro_costo_id VARCHAR(100) NULL,
    centro_costo_nombre VARCHAR(255) NULL,
    cargo VARCHAR(255) NULL,
    fecha_ingreso DATE NULL,
    correo_jefe_directo VARCHAR(254) NULL,
    correo_admin_obra VARCHAR(254) NULL,
    correo_colaborador VARCHAR(254) NULL,
    jefe_user_id VARCHAR(50) NULL,
    jefe_nombre VARCHAR(255) NULL,
    jefe_correo VARCHAR(150) NULL,
    nombres VARCHAR(150) NULL,
    apellido_paterno VARCHAR(100) NULL,
    apellido_materno VARCHAR(100) NULL,
    rut VARCHAR(20) NULL,
    tratamiento VARCHAR(20) NULL,
    genero VARCHAR(30) NULL,
    afp VARCHAR(100) NULL,
    isapre_fonasa VARCHAR(100) NULL,
    jubilado BOOLEAN NOT NULL DEFAULT FALSE,
    estado_civil VARCHAR(50) NULL,
    edad SMALLINT NULL CHECK (edad >= 0),
    fecha_nacimiento DATE NULL,
    pais_nacimiento VARCHAR(100) NULL,
    region_nacimiento VARCHAR(100) NULL,
    nacionalidad VARCHAR(80) NULL,
    nacionalidad_ext VARCHAR(100) NULL,
    telefono VARCHAR(30) NULL,
    domicilio VARCHAR(255) NULL,
    villa VARCHAR(150) NULL,
    numero_direccion VARCHAR(30) NULL,
    num_depto VARCHAR(30) NULL,
    region VARCHAR(100) NULL,
    ciudad VARCHAR(100) NULL,
    comuna VARCHAR(100) NULL,
    email_personal VARCHAR(254) NULL,
    banco VARCHAR(100) NULL,
    metodo_pago VARCHAR(50) NULL,
    numero_cuenta VARCHAR(50) NULL,
    sueldo_liquido INTEGER NULL CHECK (sueldo_liquido >= 0),
    dias_contrato INTEGER NULL CHECK (dias_contrato >= 0),
    cuenta_gasto VARCHAR(150) NULL,
    tipo_contrato VARCHAR(50) NULL,
    termino_contrato VARCHAR(255) NULL,
    fecha_termino_ito DATE NULL,
    tipo_jornada VARCHAR(30) NULL,
    horario VARCHAR(120) NULL,
    observaciones TEXT NULL,
    doc_domicilio VARCHAR(100) NULL,
    doc_titulo VARCHAR(100) NULL,
    doc_afp VARCHAR(100) NULL,
    doc_salud VARCHAR(100) NULL,
    doc_cedula VARCHAR(100) NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE_JEFE_TERRENO',
    aprobado_jefe_por VARCHAR(150) NULL,
    aprobado_jefe_at TIMESTAMPTZ NULL,
    aprobado_admin_por VARCHAR(150) NULL,
    aprobado_admin_at TIMESTAMPTZ NULL,
    aprobado_rrhh_por VARCHAR(150) NULL,
    aprobado_rrhh_at TIMESTAMPTZ NULL,
    rechazo_comentario TEXT NULL,
    rechazo_por VARCHAR(150) NULL,
    rechazo_at TIMESTAMPTZ NULL,
    creado_por VARCHAR(150) NULL,
    creado_por_id INTEGER NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS sipo_ficha_ingreso_estado_idx ON sipo_ficha_ingreso (estado);

CREATE TABLE IF NOT EXISTS sipo_solicitud_historial (
    id BIGSERIAL PRIMARY KEY,
    solicitud INTEGER NOT NULL CHECK (solicitud >= 0),
    estado_anterior INTEGER NOT NULL,
    estado_nuevo INTEGER NOT NULL,
    usuario VARCHAR(150) NOT NULL,
    comentario TEXT NOT NULL DEFAULT '',
    fecha_creacion TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS sipo_solicitud_historial_solicitud_idx
    ON sipo_solicitud_historial (solicitud);

CREATE TABLE IF NOT EXISTS sipo_candidato_acceso (
    id BIGSERIAL PRIMARY KEY,
    candidato_id VARCHAR(100) NOT NULL UNIQUE,
    sip_id INTEGER NOT NULL,
    token UUID NOT NULL UNIQUE,
    expira_at TIMESTAMPTZ NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS sipo_ficha_acceso (
    id BIGSERIAL PRIMARY KEY,
    ficha_id INTEGER NOT NULL UNIQUE,
    token UUID NOT NULL UNIQUE,
    expira_at TIMESTAMPTZ NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Verificación
SELECT table_name
FROM information_schema.tables
WHERE table_schema = current_schema()
  AND table_name LIKE 'sipo_%'
ORDER BY 1;
