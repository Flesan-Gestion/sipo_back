# Auditoría de Notificaciones por Correo — SIPO Legado (PHP)

**Fecha:** 2026-03-21  
**Alcance:** `SIPO_LEGACY/`  
**Objetivo:** Inventariar eventos, destinatarios, asuntos y estructura HTML para recrearlos en `sipo_back/` (PASO 5 — Fase 1).  
**Estado:** Fase 2 implementada — solo correos vivos del §3.  
**Override prueba:** `SIP_EMAIL_FORCE_OVERRIDE=si` → todo a `SIP_EMAIL_TEST_OVERRIDE` con destinatarios reales en el asunto.

---

## 1. Resumen ejecutivo

| Ítem | Hallazgo |
|------|----------|
| Motor | **PHPMailer** (SMTP Gmail), HTML inline (sin templates `.html` externos) |
| Archivo único de envío | `class_sip_obra.php` |
| Orquestación | `contr_sip_obra.php` ← AJAX desde `view_rrhh_sip_obra_2.php` |
| From | `equipo_desarrollo@flesan.cl` / display `"Sip Obra"` (o `"Creacion trabajadores Builder"`) |
| SMTP | `smtp.gmail.com:587`, auth con app password **hardcodeada** en cada función |
| Flujo Obra V2 relevante | Destinatarios activos vía `cf_rrhh_sip_adm` / `cf_rrhh_sip_as` |
| Flujo SIP “clásico” | Muchas funciones con `addAddress` **comentados** → envío muerto |
| Creación obra (`addsip22`) | **No envía correo** |

**Prioridad para SIPO V2 (correos “vivos” del flujo Obra):**

1. Paso a revisión / selección (`Actualizacion_Correo`)
2. Error creación Builder
3. Finalizar SIP Obra
4. Notificación de Contrato
5. Notificación de Control de Asistencia (Builder)
6. Rechazo de documentos (con CCO RRHH)

---

## 2. Configuración SMTP (común)

| Parámetro | Valor legado |
|-----------|--------------|
| Librería | PHPMailer (`IsSMTP`, `isHTML(true)`, UTF-8) |
| Host | `smtp.gmail.com` |
| Puerto | `587` |
| From | `equipo_desarrollo@flesan.cl` |
| Username | `equipo_desarrollo@flesan.cl` |
| Password | App password Gmail embebida en código (~25 bloques) |
| Includes | `/var/www/html/controlflujo/PHPMailer/src/{Exception,PHPMailer,SMTP}.php` |

**Plantilla visual común**

- Tabla ~600px, centrada
- Header: imagen PNG/JPG en `https://www.flesanmvi.com/controlflujo/system/view/sip/img/`
- Filas / acentos naranja `#FDA600`
- Botón CTA (“IR A LA PAGINA” / Portal)
- Footer: `footer_notificacion_2020.png`
- Disclaimer + contacto `jorge.barrozo@flesan.cl`

---

## 3. Correos activos — Flujo SIP OBRA (priorizar en V2)

### 3.1 Paso a revisión / Notificación de Selección

| Campo | Detalle |
|-------|---------|
| **ID propuesto V2** | `obra_paso_revision` / `obra_seleccion` |
| **Trigger UI** | Botón sobre (`actualiz_correo`) |
| **Action** | `Actualizacion_Correo` |
| **Función** | `sendNotificacionRechazoProceso2($sip_id)` *(nombre engañoso: no es rechazo)* |
| **Cuándo** | Si `cf_rrhh_sip_status < 7`: crea en Builder, pasa status **7**, envía mail a Adm. Si status **== 7**: marca seleccionados, obra status **10**, To comentados |
| **Para** | `cf_rrhh_sip_adm` (cuando status &lt; 7) |
| **CC / CCO** | — |
| **Asunto** | `{Y/m/d} [SIP OBRA] Notificación de Selección` |
| **Cuerpo** | Header `h_sip_nsel1.png`; saludo Adm; N trabajadores + empresa/UN/CC; CTA → `view_rrhh_sip_obra_2?{id},2\|3` |
| **Referencias** | `contr_sip_obra.php` ~98–101; `class_sip_obra.php` ~4110–6129 (mail ~6070–6125); `view_rrhh_sip_obra_2.php` ~1577–1587 |

---

### 3.2 Error creación trabajadores en Builder

| Campo | Detalle |
|-------|---------|
| **ID propuesto V2** | `obra_error_builder` |
| **Trigger** | Embebido en `sendNotificacionRechazoProceso2` si API Builder falla |
| **Para** | Hardcode: `jorge.barrozo@flesan.cl`, `administrativos-2025-grupo-flesan@flesan.cl`, `supervisoresrh2022@flesan.cl`, `alejandro.jara@flesan.cl` |
| **CC / CCO** | — |
| **From display** | `"Creacion trabajadores Builder"` |
| **Asunto** | `{d/m/Y} Colaboradores NO creados en Builder SIP_OBRA: {obra_id}` |
| **Cuerpo** | Error API + nombre colaborador + N° SIP |
| **Referencias** | `class_sip_obra.php` ~4254–4305 |

---

### 3.3 Finalizar SIP Obra

| Campo | Detalle |
|-------|---------|
| **ID propuesto V2** | `obra_finalizada` |
| **Trigger UI** | `Finalizar_SIP_obra()` |
| **Action** | `Finalizar` |
| **Función** | `Finalizar_SIP_OBRA($sip_id, $correo)` |
| **Cuándo** | UPDATE status obra = **10**; candidatos `seleccionado=2` |
| **Para** | `cf_rrhh_sip_adm` + `cf_rrhh_sip_as` |
| **CC / CCO** | — |
| **Asunto** | `{Y/m/d} [SIP OBRA] Notificación de Selección` *(mismo subject que 3.1)* |
| **Cuerpo** | SIP finalizado; N contratos listos / Builder; CTA a ficha obra |
| **Referencias** | `contr_sip_obra.php` ~110–113; `class_sip_obra.php` ~6145–6232 |

---

### 3.4 Notificación de Contrato

| Campo | Detalle |
|-------|---------|
| **ID propuesto V2** | `obra_contrato_disponible` |
| **Trigger UI** | `.aproCand` |
| **Action** | `updateCandidatoContratacion` |
| **Función** | `updateCandidatoContratacion(...)` |
| **Cuándo** | `cf_rrhh_sip_obra_candidato_seleccionado = 2` OK |
| **Para** | POST `correo` y `correo1` (UI: adm / as vía `data-correo` / `data-correo1`) |
| **CC / CCO** | — |
| **Asunto** | `{Y/m/d} [SIP OBRA] Notificación de Contrato` |
| **Cuerpo** | “Administrador y Asistente de Obra”; contrato de `{NAME}` disponible para firma; header `h_sip_nsel1.png` |
| **Referencias** | `contr_sip_obra.php` ~116–120; `class_sip_obra.php` ~3976–4038 |

---

### 3.5 Notificación de Control de Asistencia (Builder OK)

| Campo | Detalle |
|-------|---------|
| **ID propuesto V2** | `obra_builder_ok` |
| **Trigger UI** | `.aproBuild` |
| **Action** | `updatebuilder` |
| **Función** | `updateBuilder(...)` |
| **Cuándo** | `cf_rrhh_sip_obra_candidato_estado_builder = 1` OK |
| **Para** | POST `correo` / `correo1` |
| **Asunto** | `{Y/m/d} [SIP OBRA] Notificación de Control de Asistencia` |
| **Cuerpo** | “Ya esta creado en el control de asistencia {NAME}” |
| **Referencias** | `contr_sip_obra.php` ~123–127; `class_sip_obra.php` ~4041–4093 |

---

### 3.6 Rechazo de documentos (Obra)

| Campo | Detalle |
|-------|---------|
| **ID propuesto V2** | `obra_rechazo_documentos` |
| **Trigger** | `action=update_status_docu1` |
| **Función** | `Update_Status_Docu1(...)` |
| **Cuándo** | `estado_docu == 2` (rechazo); deselecciona candidato |
| **Para** | `cf_rrhh_sip_adm`, `cf_rrhh_sip_as` |
| **CCO** | `jorge.barrozo@flesan.cl`, `sofia.figueroa@flesan.cl`, `maria.cayuqueo@flesan.cl`, `manuel.pacha@flesan.cl`, `nelson.aravena@flesan.cl`, `marco.martinez@flesan.cl`, `carolina.zavala@flesan.cl`, `carolina.carreno@flesan.cl` |
| **Asunto** | `{Y/m/d} [SIP OBRA] Notificación de Aprobacion de Selección` *(engañoso: es rechazo docs)* |
| **Cuerpo** | Header `h_nap_sip.png`; docs rechazados + `{razones}`; CTA |
| **Referencias** | `contr_sip_obra.php` ~144–148; `class_sip_obra.php` ~6381–6465 |

> Nota: `update_status_docu` (sin “1”) **no envía mail**.

---

### 3.7 Aprobación de selección (estado obra 8) — TO vacío

| Campo | Detalle |
|-------|---------|
| **ID propuesto V2** | `obra_aprobacion_seleccion` *(opcional / revisar)* |
| **Action** | `updateStatusCandidato` → `updateCandidato` |
| **Cuándo** | Solo si `estado == 8` |
| **Para** | **Ninguno activo** (lista RRHH comentada) |
| **Asunto** | `{Y/m/d} [SIP OBRA] Notificación de Aprobacion de Selección` |
| **Referencias** | `contr_sip_obra.php` ~130–134; `class_sip_obra.php` ~6235–6326 |

---

### 3.8 Actualizacion_Correo2 — TO vacío

| Campo | Detalle |
|-------|---------|
| **Action** | `Actualizacion_Correo2` → `sendNotificacionRechazoProceso3` |
| **Cuándo** | Obra status **3**; cuenta rechazos selección |
| **Para** | **Ninguno activo** |
| **Asunto** | `{Y/m/d} [SIP OBRA] Notificación de Aprobacion de Selección` |
| **Cuerpo** | “Estimado/a RRHH”; N trabajadores; link `view_rrhh_sip_obra_4` |
| **Referencias** | `contr_sip_obra.php` ~158–161; `class_sip_obra.php` ~6476–6567 |

---

## 4. Flujo SIP “clásico” (legado no-obra / ger–jef)

Muchas funciones existen pero con destinatarios comentados (`SIN TO`). Útiles como referencia de copy/asunto si se reactivan.

| Función | Evento | Asunto (patrón) | Para | Estado |
|---------|--------|-----------------|------|--------|
| `sendNotificacionCreacion` | `insertSIP` | `[SIP OBRA] Notificación de Creación` | ger / jef (`$email`) | **Activo** |
| `sendNotificacionAprobacion` | `aprobar_SIP` / `rollback_SIP` | `Notificación Aprobación` | `cf_rrhh_sip_jef` | **Activo** |
| `sendNotificacionRechazo` | `rechazar_SIP` | `Notificación de Rechazo` | SIN TO | Muerto |
| `sendNotificacionJOBIDAsociado` | `addJobId` | `Notificación de Publicación de Aviso` | SIN TO | Muerto |
| `ActualizacionCorreo()` (≠ action Actualizacion_Correo) | status 5 | `Notificación Selección de Candidato` | SIN TO | Muerto |
| `sendNotificacionET` | etapa `et` | Entrevista Técnica | SIN TO | Muerto |
| `sendNotificacionEP` | etapa `ep` / `contra` | Entrevista Psicolaboral | SIN TO | Muerto |
| `sendNotificacionIP` | etapa `ip` | Informe Psicolaboral | SIN TO | Muerto |
| `sendNotificacionLlam` | etapa `lc` | Llamada Candidato | SIN TO | Muerto |
| `sendNotificacionCart` | etapa `co` | Carta Oferta | SIN TO | Muerto |
| `sendNotificacionSeleccion` | etapa `sel` | Selección / Bienvenida / Asignaciones | Bienvenida: correo candidato; resto SIN TO | Parcial |
| `sendNotificacionFinalizado` | `finalizar` | Finalización de Proceso | SIN TO | Muerto |
| `sendNotificacionAceptaDocu` | checklist aceptar | Finalización de Proceso | SIN TO | Muerto |
| `sendNotificacionRechazoDocu` | checklist rechazar | Rechazo de Documento | SIN TO | Muerto |
| `sendNotificacionRechazoProceso` | rechazo proceso | Rechazo Proceso de Selección | correo candidato | Activo (texto placeholder) |
| `sendNotificacionRechazoColaborador` | `cancel_sip` | Rechazo de Colaborador | SIN TO | Muerto |

**Headers de imagen (SIP clásico):**  
`h_nc_sip.png`, `h_nap_sip.png`, `h_nre_sip.png`, `h_sip_nsel.png`, `h_nac_sip.png`, `h_sip_net.png`, `h_sip_nep.png`, `h_sip_nip.png`, `h_sip_nfin.png`, `header_notificacionLLAMADA.jpg`, `header_notificacionCARTA_OFERTA.jpg`, `header_notificacionERROR_DOCUMENTOS.jpg`, `header_notificacionRECHAZO_COLAB.jpg`, `top_bienvenida.png`, `bot_bienvenida.png`, `fin.png`.

---

## 5. Mapa Action → Mail

```
Actualizacion_Correo          → sendNotificacionRechazoProceso2 (+ mail error Builder)
Finalizar                     → Finalizar_SIP_OBRA
updateCandidatoContratacion   → mail Contrato
updatebuilder                 → mail Control Asistencia
update_status_docu1           → Update_Status_Docu1 (rechazo + CCO)
updateStatusCandidato         → updateCandidato (estado==8, TO vacío)
Actualizacion_Correo2         → sendNotificacionRechazoProceso3 (TO vacío)
insert_sip                    → sendNotificacionCreacion
aprobar_SIP / rollback_SIP    → sendNotificacionAprobacion
rechazar_SIP                  → sendNotificacionRechazo (TO vacío)
update_status_seleccion       → ET / EP / IP / Llam / Cart / Sel / Finalizado / …
update_status_check           → AceptaDocu / RechazoDocu
cancel_sip                    → RechazoColaborador (TO vacío)
addsip22                      → (sin mail)
cancelada / elim_trab         → (sin mail)
```

---

## 6. Destinatarios — campos y hardcodes

### Dinámicos (BD / POST)

| Campo / origen | Rol |
|----------------|-----|
| `cf_rrhh_sip_adm` | Administrador de Obra |
| `cf_rrhh_sip_as` | Asistente de Obra |
| `cf_rrhh_sip_ger` / `cf_rrhh_sip_jef` | Flujo SIP clásico |
| `cf_rrhh_sip_create_user` | Creador (permisos UI; no siempre To) |
| `cf_rrhh_sip_candidato_correo` | Candidato (bienvenida / rechazo proceso) |
| POST `correo` / `correo1` | Contrato y Builder desde UI |

### Hardcodes activos

| Email | Uso |
|-------|-----|
| `equipo_desarrollo@flesan.cl` | From + SMTP |
| `jorge.barrozo@flesan.cl` | CCO rechazo docs; To error Builder; mailto disclaimer |
| `administrativos-2025-grupo-flesan@flesan.cl` | Error Builder |
| `supervisoresrh2022@flesan.cl` | Error Builder |
| `alejandro.jara@flesan.cl` | Error Builder |
| `sofia.figueroa@flesan.cl` | CCO rechazo docs |
| `maria.cayuqueo@flesan.cl` | CCO rechazo docs |
| `manuel.pacha@flesan.cl` | CCO rechazo docs |
| `nelson.aravena@flesan.cl` | CCO rechazo docs |
| `marco.martinez@flesan.cl` | CCO rechazo docs |
| `carolina.zavala@flesan.cl` | CCO rechazo docs |
| `carolina.carreno@flesan.cl` | CCO rechazo docs |

---

## 7. Acciones sin correo

| Action / función | Nota |
|------------------|------|
| `addsip22` | Crea obra status 6, sin mail |
| `Cancelada` | Status 9; instancia mail sin uso |
| `elim_trab` | Soft-delete candidato |
| `update_status_docu` | Solo DB |
| `updateStatusCandidatos` | Solo DB |
| `Desactivar_Job_ID` | Solo flag |
| Validación correo AbstractAPI | No es notificación |

---

## 8. Hallazgos críticos para paridad V2

1. **Credencial SMTP hardcodeada** — externalizar a `.env` (ya previsto en Django).
2. **Subjects reutilizados / engañosos** (“Aprobacion de Selección” = rechazo docs; “Selección” = paso revisión y finalizar).
3. **Decenas de notificaciones SIP clásico sin destinatario** — no clonar ciegamente.
4. **`addsip22` (creación obra) no notifica** — decidir si V2 debe notificar en `POST /sipo/`.
5. **Nombres de funciones engañosos:** `sendNotificacionRechazoProceso2` = paso a Adm/Builder.
6. **Bug:** etapa `rh` llama `sendNotificacionRechazoProceso2` con 2 args; la fn obra espera 1.
7. **Bienvenida** con texto `"Texto de prueba[]"` en legado.
8. Un solo archivo de mails: `class_sip_obra.php`.

---

## 9. Mapeo SIPO V2 (implementado)

| Evento V2 | Trigger | Función |
|-----------|---------|---------|
| Paso a revisión | `cambiar_estado` 6→7 | `send_email_paso_revision` |
| Error Builder | fallo iBuilder en paso revisión | `send_email_error_builder` |
| Finalizar / aprobar contratación | `aprobar_contratacion_obra` | `send_email_obra_finalizada` |
| Contrato disponible | mismo flujo, por candidato | `send_email_contrato_disponible` |
| Builder OK | `crear_trabajador_ibuilder` OK | `send_email_builder_ok` |
| Rechazo documentos | listo (`send_email_rechazo_documentos`) | *sin endpoint V2 aún* |

**Plantillas:** `sipo/templates/emails/`  
**Servicio:** `sipo/services/notifications.py`  
**Tests:** `sipo/tests/test_notifications.py`

---

## 10. Override de prueba (paridad SIP_NUEVO)

```
SIP_EMAIL_FORCE_OVERRIDE=si
SIP_EMAIL_TEST_OVERRIDE=martin.norambuena@flesan.cl
```

Valores truthy: `si`, `sí`, `true`, `1`, `yes`, `on`.

---

*Documento generado a partir de análisis de `SIPO_LEGACY/class_sip_obra.php`, `contr_sip_obra.php` y `view_rrhh_sip_obra_2.php`.*
