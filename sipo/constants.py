SIPO_ID_CUTOFF = 1159

SIPO_ROL_ADMIN = 1
SIPO_ROL_RRHH = 2
SIPO_ROL_SUPERVISOR = 4

SIPO_STATUS_EN_ESPERA = 6
SIPO_STATUS_EN_REVISION = 7
SIPO_STATUS_APROBADA = 8
SIPO_STATUS_CANCELADA = 9
SIPO_STATUS_FINALIZADA = 10
SIPO_STATUS_REGISTRO_DT = 11

ESTADO_FILTROS = {
    'Activas': [SIPO_STATUS_EN_ESPERA, SIPO_STATUS_EN_REVISION, SIPO_STATUS_APROBADA],
    'En espera': SIPO_STATUS_EN_ESPERA,
    'En revision': SIPO_STATUS_EN_REVISION,
    'Aprobada': SIPO_STATUS_APROBADA,
    'Cancelada': SIPO_STATUS_CANCELADA,
    'Finalizada': SIPO_STATUS_FINALIZADA,
    'Registro DT': SIPO_STATUS_REGISTRO_DT,
}

SIPO_ESTADO_LABELS = {
    1: 'Nueva',
    3: 'Iniciada',
    4: 'Rechazada',
    5: 'Seleccionando',
    SIPO_STATUS_EN_ESPERA: 'En espera',
    SIPO_STATUS_EN_REVISION: 'En revisión',
    SIPO_STATUS_APROBADA: 'Aprobada',
    SIPO_STATUS_CANCELADA: 'Cancelada',
    SIPO_STATUS_FINALIZADA: 'Finalizada',
    SIPO_STATUS_REGISTRO_DT: 'Registro DT',
}

# Transiciones Admin/RRHH (roles 1 y 2). Cancelar (<9 -> 9) solo Admin.
SIPO_TRANSICIONES_APROBACION = {
    SIPO_STATUS_EN_ESPERA: {SIPO_STATUS_EN_REVISION},
    SIPO_STATUS_EN_REVISION: {SIPO_STATUS_FINALIZADA, SIPO_STATUS_REGISTRO_DT},
}

SIPO_ACCION_ESTADO = {
    SIPO_STATUS_EN_REVISION: {
        'codigo': 'pasar_revision',
        'label': 'Pasar a Revisión',
        'severity': 'info',
    },
    SIPO_STATUS_FINALIZADA: {
        'codigo': 'finalizar',
        'label': 'Aprobar / Finalizar',
        'severity': 'success',
    },
    SIPO_STATUS_REGISTRO_DT: {
        'codigo': 'registro_dt',
        'label': 'Registro DT',
        'severity': 'success',
    },
    SIPO_STATUS_CANCELADA: {
        'codigo': 'cancelar',
        'label': 'Cancelar',
        'severity': 'danger',
    },
}

SIPO_CANDIDATO_ACTIVO = 1
SIPO_CANDIDATO_ELIMINADO = 0
SIPO_MAX_CANDIDATOS = 5

# Regla Chivato Huechún: colación/movilización forzadas a $1
CC_CHIVATO_HUECHUN = 'CFMCFM130048'
COL_MOV_CHIVATO_HUECHUN = 1

# Remuneraciones obra (FASE 1)
IMM_ACTUAL = 553_553  # piso sueldo base
SUELDO_LIQUIDO_MINIMO = 585_000  # piso sueldo líquido pactado

# Segregación país / Grupo 2 (sap_maestro_empresa_dep_un_cc.external_code_pais)
EXTERNAL_CODE_PAIS_CHILE = '10000001'
EXTERNAL_CODE_PAIS_GRUPO_2 = '10000004'

SIPO_CANDIDATO_SIN_SELECCION = 0
SIPO_CANDIDATO_SELECCIONADO = 1
SIPO_CANDIDATO_CONTRATADO_SAP = 2

SIPO_LIST_ONLY_FIELDS = (
    'cf_rrhh_sip_id',
    'cf_rrhh_sip_adm',
    'cf_rrhh_sip_as',
    'cf_rrhh_sip_create_user',
    'cf_rrhh_sip_rut',
    'cf_rrhh_sip_cc',
    'cf_rrhh_sip_status',
    'cf_rrhh_sip_razonsocial',
    'cf_rrhh_sip_uni',
    'cf_rrhh_sip_create_date',
    'cf_rrhh_sip_nombre_uni',
    'cf_rrhh_sip_nombre_cc',
    'cf_rrhh_sip_status_date',
    'cf_rrhh_sip_status_user',
)
