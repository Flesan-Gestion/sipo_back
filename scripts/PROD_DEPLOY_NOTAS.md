# Deploy SIPO V2 a producción — notas

## Dos bases distintas

| Base | Variable `.env` | Qué lleva V2 nuevo |
|------|-----------------|--------------------|
| **MySQL** (legado Obra) | `DB_MYSQL_*` | `cf_rrhh_sip_perfil_empresa`, `cf_rrhh_sip_perfil_cc`, roles 4 y 5 |
| **PostgreSQL** (app) | `DB_*_APP` | `sipo_ficha_ingreso`, `sipo_solicitud_historial`, `sipo_candidato_acceso`, `sipo_ficha_acceso` + tablas Django |

Las tablas legado (`cf_rrhh_sip_obra`, candidatos, etc.) **ya existen** en MySQL prod; no se recrean.

## Orden recomendado

1. Ejecutar `scripts/prod_mysql_sip_db_v2.sql` en MySQL **prod** (tablas alcance, roles 4/5 **y columnas V2** en `cf_rrhh_sip_candidato_obra`: jefe_*, segundo_nombre, sueldo_base, bono_mineria + `external_code_pais` en maestro CC).
2. Apuntar `.env` al Postgres **prod** de la app.
3. Preferido: `python manage.py migrate` (crea tablas Django + registra migraciones).
4. Alternativa: `scripts/prod_postgres_app_v2.sql` y luego igual `migrate` (Django creará lo que falte / marcará estado).
5. Ajustar flags prod (abajo).
6. Asignar perfiles a roles Supervisor (4) / Jefe Terreno (5) en MySQL.

### Error típico 1054 (Unknown column …jefe_user_id)

Falta el ALTER de columnas V2 en MySQL. Re-ejecutar `prod_mysql_sip_db_v2.sql` (idempotente) o solo:

```sql
ALTER TABLE cf_rrhh_sip_candidato_obra
  ADD COLUMN cf_rrhh_sip_obra_candidato_jefe_user_id VARCHAR(50) NULL,
  ADD COLUMN cf_rrhh_sip_obra_candidato_jefe_nombre VARCHAR(255) NULL,
  ADD COLUMN cf_rrhh_sip_obra_candidato_jefe_correo VARCHAR(150) NULL;
```

## Flags `.env` producción

```env
DEBUG=False
SECRET_KEY=<secreto fuerte distinto al de QA>
ALLOWED_HOSTS=tu-dominio-api.flesan.cl,localhost
HOST=tu-dominio-api.flesan.cl
WEB_HOST=https://tu-dominio-front.flesan.cl
WEB_URL=https://tu-dominio-front.flesan.cl

DEV_AUTH_ALLOWED_EMAILS=
# DEV_AUTH_AUTO_CREATE no se usa en código hoy; dejar false por claridad
DEV_AUTH_AUTO_CREATE=false

SIP_EMAIL_FORCE_OVERRIDE=no
SIP_EMAIL_ENABLED=true

SAP_SF_SYNC_ENABLED=true
# URL/credenciales SAP prod (no preview)
IBUILDER_SYNC_ENABLED=True
CHECK_IBUILDER_SAP_ENABLED=True
```
