from django.urls import path

from .views_ficha import (
    SipoFichaAccesoView,
    SipoFichaAdjuntoView,
    SipoFichaAprobarView,
    SipoFichaDetailView,
    SipoFichaPdfView,
    SipoFichaRechazarView,
    SipoFichaRetrocederView,
    SipoFichasListCreateView,
)
from .views_users import (
    SipoMiAlcanceView,
    SipoPerfilesListView,
    SipoUsuarioDetailView,
    SipoUsuariosListCreateView,
)
from .views_excel import SipoExportarExcelView
from .views_cargos_horarios import SipoConfigCargosView, SipoConfigEmpresasView, SipoConfigHorariosView
from .views_maestros import SipoCentrosCostoView, SipoRazonesSocialesView
from .views_portal import SipoCandidatoAccesoView, SipoPortalCandidatoView
from .views import (
    SipoCandidatoDetailView,
    SipoCandidatoDocumentoView,
    SipoCandidatoMaestrosView,
    SipoCandidatosView,
    SipoCandidatoToggleRevisionDtView,
    SipoCandidatoToggleSeleccionView,
    SipoCandidatoToggleSeleccionByIdView,
    SipoCandidatosSeleccionadosView,
    SipoCandidatosSeleccionarTodosView,
    SipoCandidatoUploadDocView,
    SipoMaestrosView,
    SipoObraCambiarEstadoView,
    SipoObraCancelView,
    SipoObraDetailView,
    SipoObraListView,
    SipoPersonalPlantaView,
    SipoReintegrarDetalleView,
    SipoReintegrarListView,
    SipoAprobarContratacionView,
    SipoSyncSapView,
    SipoValidarCorreoView,
    SipoValidarRutView,
)

urlpatterns = [
    path('sipo/usuarios/', SipoUsuariosListCreateView.as_view(), name='sipo-usuarios'),
    path('sipo/usuarios/<int:usuario_id>/', SipoUsuarioDetailView.as_view(), name='sipo-usuario-detail'),
    path('sipo/perfiles/', SipoPerfilesListView.as_view(), name='sipo-perfiles'),
    path('sipo/me/alcance/', SipoMiAlcanceView.as_view(), name='sipo-me-alcance'),
    path('sipo/fichas/', SipoFichasListCreateView.as_view(), name='sipo-fichas'),
    path('sipo/fichas/<int:ficha_id>/acceso/', SipoFichaAccesoView.as_view(), name='sipo-ficha-acceso'),
    path('sipo/fichas/<int:ficha_id>/', SipoFichaDetailView.as_view(), name='sipo-ficha-detail'),
    path('sipo/fichas/<int:ficha_id>/pdf/', SipoFichaPdfView.as_view(), name='sipo-ficha-pdf'),
    path(
        'sipo/fichas/<int:ficha_id>/aprobar/',
        SipoFichaAprobarView.as_view(),
        name='sipo-ficha-aprobar',
    ),
    path(
        'sipo/fichas/<int:ficha_id>/rechazar/',
        SipoFichaRechazarView.as_view(),
        name='sipo-ficha-rechazar',
    ),
    path(
        'sipo/fichas/<int:ficha_id>/retroceder/',
        SipoFichaRetrocederView.as_view(),
        name='sipo-ficha-retroceder',
    ),
    path(
        'sipo/fichas/<int:ficha_id>/adjuntos/<str:doc_type>/',
        SipoFichaAdjuntoView.as_view(),
        name='sipo-ficha-adjunto',
    ),
    path(
        'sipo/maestros/personal-planta/',
        SipoPersonalPlantaView.as_view(),
        name='sipo-personal-planta',
    ),
    path('sipo/maestros/', SipoMaestrosView.as_view(), name='sipo-maestros'),
    path(
        'sipo/razones-sociales/',
        SipoRazonesSocialesView.as_view(),
        name='sipo-razones-sociales',
    ),
    path(
        'sipo/centros-costo/',
        SipoCentrosCostoView.as_view(),
        name='sipo-centros-costo',
    ),
    path(
        'sipo/candidatos/maestros/',
        SipoCandidatoMaestrosView.as_view(),
        name='sipo-candidatos-maestros',
    ),
    path(
        'sipo/candidatos/upload-doc/',
        SipoCandidatoUploadDocView.as_view(),
        name='sipo-candidatos-upload-doc',
    ),
    path(
        'sipo/candidatos/reintegrar-list/',
        SipoReintegrarListView.as_view(),
        name='sipo-reintegrar-list',
    ),
    path(
        'sipo/candidatos/reintegrar-detalle/<path:rut>/',
        SipoReintegrarDetalleView.as_view(),
        name='sipo-reintegrar-detalle',
    ),
    path(
        'sipo/candidatos/validar-correo/',
        SipoValidarCorreoView.as_view(),
        name='sipo-validar-correo',
    ),
    path(
        'sipo/candidatos/validar-rut/',
        SipoValidarRutView.as_view(),
        name='sipo-validar-rut',
    ),
    path(
        'sipo/public/ficha/<uuid:token>/',
        SipoPortalCandidatoView.as_view(),
        name='sipo-portal-ficha',
    ),
    path('sipo/', SipoObraListView.as_view(), name='sipo-list'),
    path('sipo/exportar-excel/', SipoExportarExcelView.as_view(), name='sipo-exportar-excel'),
    path('sipo/config/empresas/', SipoConfigEmpresasView.as_view(), name='sipo-config-empresas'),
    path('sipo/config/cargos/', SipoConfigCargosView.as_view(), name='sipo-config-cargos'),
    path('sipo/config/horarios/', SipoConfigHorariosView.as_view(), name='sipo-config-horarios'),
    path('sipo/<int:sip_id>/cancelar/', SipoObraCancelView.as_view(), name='sipo-cancelar'),
    path(
        'sipo/<int:sip_id>/cambiar-estado/',
        SipoObraCambiarEstadoView.as_view(),
        name='sipo-cambiar-estado',
    ),
    path('sipo/<int:sip_id>/candidatos/', SipoCandidatosView.as_view(), name='sipo-candidatos'),
    path(
        'sipo/<int:sip_id>/candidatos-seleccionados/',
        SipoCandidatosSeleccionadosView.as_view(),
        name='sipo-candidatos-seleccionados',
    ),
    path(
        'sipo/<int:sip_id>/candidatos/seleccionar-todos/',
        SipoCandidatosSeleccionarTodosView.as_view(),
        name='sipo-candidatos-seleccionar-todos',
    ),
    path(
        'sipo/<int:sip_id>/candidatos/<str:candidato_id>/toggle-seleccion/',
        SipoCandidatoToggleSeleccionView.as_view(),
        name='sipo-candidato-toggle-seleccion',
    ),
    path(
        'sipo/candidatos/<str:candidato_id>/toggle-seleccion/',
        SipoCandidatoToggleSeleccionByIdView.as_view(),
        name='sipo-candidato-toggle-seleccion-global',
    ),
    path(
        'sipo/<int:sip_id>/candidatos/<str:candidato_id>/documento/<str:doc_type>/',
        SipoCandidatoDocumentoView.as_view(),
        name='sipo-candidato-documento',
    ),
    path(
        'sipo/<int:sip_id>/candidatos/<str:candidato_id>/acceso/',
        SipoCandidatoAccesoView.as_view(),
        name='sipo-candidato-acceso',
    ),
    path(
        'sipo/<int:sip_id>/candidatos/<str:candidato_id>/',
        SipoCandidatoDetailView.as_view(),
        name='sipo-candidato-detail',
    ),
    path(
        'sipo/candidatos/<str:candidato_id>/toggle-revision-dt/',
        SipoCandidatoToggleRevisionDtView.as_view(),
        name='sipo-candidato-toggle-revision-dt',
    ),
    path('sipo/<int:sip_id>/sync-sap/', SipoSyncSapView.as_view(), name='sipo-sync-sap'),
    path(
        'sipo/<int:sip_id>/aprobar-contratacion/',
        SipoAprobarContratacionView.as_view(),
        name='sipo-aprobar-contratacion',
    ),
    path('sipo/<int:sip_id>/', SipoObraDetailView.as_view(), name='sipo-detail'),
]
