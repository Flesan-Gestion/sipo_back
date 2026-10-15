-- =============================================================================
-- SIPO V2 → MySQL (sip_db / gestionf_sip_obra PRODUCCIÓN)
-- Idempotente. Ejecutar en DBeaver contra gestionf_sip_obra.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0) Helper: agregar columna solo si no existe
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sipo_v2_add_column_if_missing;
DELIMITER $$
CREATE PROCEDURE sipo_v2_add_column_if_missing(
    IN p_table VARCHAR(128),
    IN p_column VARCHAR(128),
    IN p_definition VARCHAR(512)
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = p_table
          AND COLUMN_NAME = p_column
    ) THEN
        SET @ddl = CONCAT(
            'ALTER TABLE `', p_table, '` ADD COLUMN `', p_column, '` ', p_definition
        );
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$
DELIMITER ;

-- -----------------------------------------------------------------------------
-- 1) Alcance territorial (RS / CC por perfil)
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- 2) Roles nuevos V2
-- -----------------------------------------------------------------------------
INSERT INTO cf_rrhh_sip_rol (cf_rol_id, cf_rol_name)
VALUES (4, 'Supervisor')
ON DUPLICATE KEY UPDATE cf_rol_name = 'Supervisor';

INSERT INTO cf_rrhh_sip_rol (cf_rol_id, cf_rol_name)
VALUES (5, 'Jefe de Terreno')
ON DUPLICATE KEY UPDATE cf_rol_name = 'Jefe de Terreno';

-- -----------------------------------------------------------------------------
-- 3) Columnas V2 en cf_rrhh_sip_candidato_obra (causa típica del 1054)
-- -----------------------------------------------------------------------------
CALL sipo_v2_add_column_if_missing(
    'cf_rrhh_sip_candidato_obra',
    'cf_rrhh_sip_obra_candidato_segundo_nombre',
    'VARCHAR(100) NULL'
);
CALL sipo_v2_add_column_if_missing(
    'cf_rrhh_sip_candidato_obra',
    'cf_rrhh_sip_obra_candidato_jefe_user_id',
    'VARCHAR(50) NULL'
);
CALL sipo_v2_add_column_if_missing(
    'cf_rrhh_sip_candidato_obra',
    'cf_rrhh_sip_obra_candidato_jefe_nombre',
    'VARCHAR(255) NULL'
);
CALL sipo_v2_add_column_if_missing(
    'cf_rrhh_sip_candidato_obra',
    'cf_rrhh_sip_obra_candidato_jefe_correo',
    'VARCHAR(150) NULL'
);
CALL sipo_v2_add_column_if_missing(
    'cf_rrhh_sip_candidato_obra',
    'cf_rrhh_sip_obra_sueldo_base',
    'DECIMAL(12,2) NULL'
);
CALL sipo_v2_add_column_if_missing(
    'cf_rrhh_sip_candidato_obra',
    'cf_rrhh_sip_obra_bono_mineria',
    'DECIMAL(12,2) NULL'
);

-- -----------------------------------------------------------------------------
-- 4) País en maestro CC (filtro Grupo 2)
-- -----------------------------------------------------------------------------
CALL sipo_v2_add_column_if_missing(
    'sap_maestro_empresa_dep_un_cc',
    'external_code_pais',
    'VARCHAR(50) NULL'
);

DROP PROCEDURE IF EXISTS sipo_v2_add_column_if_missing;

-- -----------------------------------------------------------------------------
-- 5) Verificación: columnas críticas que DEBEN existir
-- -----------------------------------------------------------------------------
SELECT c.COLUMN_NAME, c.COLUMN_TYPE, c.IS_NULLABLE
FROM information_schema.COLUMNS c
WHERE c.TABLE_SCHEMA = DATABASE()
  AND c.TABLE_NAME = 'cf_rrhh_sip_candidato_obra'
  AND c.COLUMN_NAME IN (
    'cf_rrhh_sip_obra_candidato_segundo_nombre',
    'cf_rrhh_sip_obra_candidato_jefe_user_id',
    'cf_rrhh_sip_obra_candidato_jefe_nombre',
    'cf_rrhh_sip_obra_candidato_jefe_correo',
    'cf_rrhh_sip_obra_sueldo_base',
    'cf_rrhh_sip_obra_bono_mineria'
  )
ORDER BY c.COLUMN_NAME;

SELECT cf_rol_id, cf_rol_name FROM cf_rrhh_sip_rol ORDER BY cf_rol_id;
SHOW TABLES LIKE 'cf_rrhh_sip_perfil_%';

-- Faltantes (debe devolver 0 filas):
SELECT expected.col AS columna_faltante
FROM (
    SELECT 'cf_rrhh_sip_obra_candidato_segundo_nombre' AS col
    UNION ALL SELECT 'cf_rrhh_sip_obra_candidato_jefe_user_id'
    UNION ALL SELECT 'cf_rrhh_sip_obra_candidato_jefe_nombre'
    UNION ALL SELECT 'cf_rrhh_sip_obra_candidato_jefe_correo'
    UNION ALL SELECT 'cf_rrhh_sip_obra_sueldo_base'
    UNION ALL SELECT 'cf_rrhh_sip_obra_bono_mineria'
) expected
LEFT JOIN information_schema.COLUMNS c
  ON c.TABLE_SCHEMA = DATABASE()
 AND c.TABLE_NAME = 'cf_rrhh_sip_candidato_obra'
 AND c.COLUMN_NAME = expected.col
WHERE c.COLUMN_NAME IS NULL;
