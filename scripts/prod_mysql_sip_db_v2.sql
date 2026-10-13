-- =============================================================================
-- SIPO V2 → MySQL (sip_db / gestionf_sip_obra PRODUCCIÓN)
-- Tablas/roles NUEVOS sobre el legado. Idempotente (IF NOT EXISTS / ON DUPLICATE).
-- NO toca cf_rrhh_sip_obra ni candidatos existentes.
-- =============================================================================

-- 1) Alcance territorial (RS / CC por perfil)
CREATE TABLE IF NOT EXISTS cf_rrhh_sip_perfil_empresa (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cf_rrhh_sip_perfil_id INT NOT NULL,
    empresa_rut VARCHAR(32) NOT NULL,
    empresa_nombre VARCHAR(200) NULL,
    UNIQUE KEY uq_perfil_empresa (cf_rrhh_sip_perfil_id, empresa_rut),
    KEY idx_perfil_empresa_perfil (cf_rrhh_sip_perfil_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS cf_rrhh_sip_perfil_cc (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cf_rrhh_sip_perfil_id INT NOT NULL,
    empresa_rut VARCHAR(32) NOT NULL,
    centro_costo_id VARCHAR(100) NOT NULL,
    centro_costo_nombre VARCHAR(200) NULL,
    UNIQUE KEY uq_perfil_cc (cf_rrhh_sip_perfil_id, centro_costo_id),
    KEY idx_perfil_cc_perfil (cf_rrhh_sip_perfil_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2) Roles nuevos V2
INSERT INTO cf_rrhh_sip_rol (cf_rol_id, cf_rol_name)
VALUES (4, 'Supervisor')
ON DUPLICATE KEY UPDATE cf_rol_name = 'Supervisor';

INSERT INTO cf_rrhh_sip_rol (cf_rol_id, cf_rol_name)
VALUES (5, 'Jefe de Terreno')
ON DUPLICATE KEY UPDATE cf_rol_name = 'Jefe de Terreno';

-- 3) (Opcional) Asignar rol a un perfil existente — descomentar y ajustar email:
-- UPDATE cf_rrhh_sip_perfil
-- SET cf_rol_id = 5
-- WHERE LOWER(TRIM(usuario_email)) = 'correo.jefe@flesan.cl';

-- Verificación
SELECT cf_rol_id, cf_rol_name FROM cf_rrhh_sip_rol ORDER BY cf_rol_id;
SHOW TABLES LIKE 'cf_rrhh_sip_perfil_%';
