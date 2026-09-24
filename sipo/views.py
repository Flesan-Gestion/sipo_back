import os

from rest_framework.views import APIView

from utils.responses import ApiResponseSuccess, Data

from .permissions import IsSipoAdmin, IsSipoAdminOrRrhh, IsSipoAuthenticated
from .serializers import (
    SipoCambiarEstadoSerializer,
    SipoCancelarSerializer,
    SipoCandidatoSeleccionadoSerializer,
    SipoCandidatoSerializer,
    SipoCandidatoWriteSerializer,
    SipoObraDetailSerializer,
    SipoObraListSerializer,
    SipoObraPatchSerializer,
    SipoObraWriteSerializer,
    SipoSeleccionarTodosSerializer,
)
from .services.candidato_docs import (
    DOC_FIELD_MAP,
    is_external_candidato_doc_url,
    resolve_local_candidato_doc_path,
    save_candidato_document,
)
from .services.candidato_maestros import get_candidato_maestros
from .services.candidato_seleccion import seleccionar_todos_candidatos, toggle_seleccion_candidato
from .services.candidatos import create_candidato, list_candidatos, soft_delete_candidato, update_candidato
from .services.candidatos_seleccionados import (
    list_candidatos_seleccionados,
    toggle_revision_dt_candidato,
)
from .services.crud import create_sipo_obra, get_obra_for_user, update_sipo_obra
from .services.email_validation import validar_correo_smtp
from .services.estados import cambiar_estado_obra
from .services.list import cancel_sipo_obra, get_sipo_list_page
from .services.maestros import get_sipo_maestros
from .services.aprobar_contratacion import aprobar_contratacion_obra
from .services.reintegrar import get_reintegrar_detalle, list_reintegrar_trabajadores
from .services.sap_sync import sync_sipo_candidatos_sap


def _pagination_params(request):
    page = int(request.query_params.get('page') or 1)
    per_page = int(
        request.query_params.get('per_page')
        or request.query_params.get('perPage')
        or 10
    )
    return page, per_page


class SipoObraListView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request):
        estado = request.query_params.get('estado', 'Activas')
        filter_text = request.query_params.get('filterText') or request.query_params.get('q')
        page, per_page = _pagination_params(request)

        records, total_records, page, per_page = get_sipo_list_page(
            estado=estado,
            user=request.user,
            page=page,
            per_page=per_page,
            filter_text=filter_text,
        )
        items = SipoObraListSerializer(records, many=True).data

        mutable = request.query_params.copy()
        mutable['page'] = str(page)
        mutable['perPage'] = str(per_page)
        request._request.GET = mutable

        data = Data(items, request, total_records)
        return ApiResponseSuccess(data).response()

    def post(self, request):
        serializer = SipoObraWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obra = create_sipo_obra(data=serializer.validated_data, user=request.user)
        item = SipoObraDetailSerializer(obra, context={'request': request}).data
        return ApiResponseSuccess(item).response()


class SipoObraDetailView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request, sip_id):
        obra = get_obra_for_user(int(sip_id), request.user)
        item = SipoObraDetailSerializer(obra, context={'request': request}).data
        return ApiResponseSuccess(item).response()

    def patch(self, request, sip_id):
        obra = get_obra_for_user(int(sip_id), request.user)
        serializer = SipoObraPatchSerializer(
            data=request.data,
            partial=True,
            context={'obra': obra, 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        obra = update_sipo_obra(
            sip_id=int(sip_id),
            data=serializer.validated_data,
            user=request.user,
        )
        item = SipoObraDetailSerializer(obra, context={'request': request}).data
        return ApiResponseSuccess(item).response()


class SipoObraCancelView(APIView):
    permission_classes = [IsSipoAdmin]

    def post(self, request, sip_id):
        serializer = SipoCancelarSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        obra = cancel_sipo_obra(
            sip_id=int(sip_id),
            user=request.user,
            comentario=serializer.validated_data.get('comentario'),
        )
        item = SipoObraListSerializer(obra).data
        return ApiResponseSuccess(item).response()


class SipoObraCambiarEstadoView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def post(self, request, sip_id):
        serializer = SipoCambiarEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obra = cambiar_estado_obra(
            sip_id=int(sip_id),
            nuevo_estado=serializer.validated_data['nuevo_estado'],
            user=request.user,
            comentario=serializer.validated_data.get('comentario'),
        )
        item = SipoObraDetailSerializer(obra, context={'request': request}).data
        notificaciones = {}
        if hasattr(obra, '_email_revision'):
            notificaciones['revision'] = getattr(obra, '_email_revision', None)
            notificaciones['builder_errors'] = getattr(obra, '_email_builder_errors', [])
        if notificaciones:
            item['notificaciones'] = notificaciones
        return ApiResponseSuccess(item).response()


class SipoCandidatosView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request, sip_id):
        records = list_candidatos(int(sip_id), request.user)
        items = SipoCandidatoSerializer(records, many=True).data
        return ApiResponseSuccess(items).response()

    def post(self, request, sip_id):
        serializer = SipoCandidatoWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        candidato = create_candidato(
            sip_id=int(sip_id),
            data=serializer.validated_data,
            user=request.user,
        )
        item = SipoCandidatoSerializer(candidato).data
        return ApiResponseSuccess(item).response()


class SipoCandidatoDetailView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def patch(self, request, sip_id, candidato_id):
        serializer = SipoCandidatoWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        candidato = update_candidato(
            sip_id=int(sip_id),
            candidato_id=str(candidato_id),
            data=serializer.validated_data,
            user=request.user,
        )
        item = SipoCandidatoSerializer(candidato).data
        return ApiResponseSuccess(item).response()

    def delete(self, request, sip_id, candidato_id):
        soft_delete_candidato(
            sip_id=int(sip_id),
            candidato_id=str(candidato_id),
            user=request.user,
        )
        return ApiResponseSuccess({'deleted': True}).response()


class SipoMaestrosView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request):
        from .services.pais_segregation import normalize_pais

        rut = request.query_params.get('rut')
        pais = normalize_pais(request.query_params.get('external_code_pais'))
        data = get_sipo_maestros(rut=rut, user=request.user, external_code_pais=pais)
        return ApiResponseSuccess(data).response()


class SipoReintegrarListView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request):
        search = request.query_params.get('search') or request.query_params.get('q')
        items = list_reintegrar_trabajadores(search=search)
        return ApiResponseSuccess(items).response()


class SipoReintegrarDetalleView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request, rut):
        candidato = get_reintegrar_detalle(rut)
        item = SipoCandidatoSerializer(candidato).data
        return ApiResponseSuccess(item).response()


class SipoValidarCorreoView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request):
        from rest_framework.exceptions import ValidationError

        correo = (
            request.query_params.get('email')
            or request.query_params.get('correo')
            or ''
        ).strip()
        if not correo:
            raise ValidationError({'email': 'Debe indicar el correo.'})
        valido = validar_correo_smtp(correo)
        return ApiResponseSuccess({'valido': valido}).response()


class SipoValidarRutView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request):
        from rest_framework.exceptions import ValidationError

        from .services.candidato_validaciones import is_valid_rut
        from .services.rut_validation import validar_rut_activo

        rut = (request.query_params.get('rut') or '').strip()
        if not rut:
            raise ValidationError({'rut': 'Debe indicar el RUT.'})

        sip_id = None
        raw_sip = request.query_params.get('sip_id')
        if raw_sip:
            try:
                sip_id = int(raw_sip)
                get_obra_for_user(sip_id, request.user)
            except (TypeError, ValueError):
                raise ValidationError({'sip_id': 'sip_id inválido.'})

        valido = is_valid_rut(rut)
        result = validar_rut_activo(rut, sip_id=sip_id)
        bypass = bool(result.get('bypass'))
        activo_ibuilder_sap = False if bypass else bool(result.get('activo'))
        mensaje = '' if bypass else str(result.get('motivo') or '')

        return ApiResponseSuccess({
            'valido': valido,
            'activo_ibuilder_sap': activo_ibuilder_sap,
            'mensaje': mensaje,
            'fuente': result.get('fuente'),
            'builder_proyecto_id': result.get('builder_proyecto_id'),
        }).response()


class SipoCandidatoMaestrosView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request):
        return ApiResponseSuccess(get_candidato_maestros()).response()


class SipoCandidatoUploadDocView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def post(self, request):
        from django.conf import settings
        from rest_framework.exceptions import ValidationError

        uploaded = request.FILES.get('file') or request.FILES.get('documento')
        doc_type = request.data.get('doc_type') or request.data.get('tipo') or ''
        rut = request.data.get('rut') or ''
        try:
            sip_id = int(request.data.get('sip_id') or 0)
        except (TypeError, ValueError):
            sip_id = 0
        if not sip_id:
            raise ValidationError({'sip_id': 'Debe indicar sip_id.'})

        get_obra_for_user(sip_id, request.user)
        result = save_candidato_document(
            uploaded_file=uploaded,
            doc_type=str(doc_type),
            sip_id=sip_id,
            rut=str(rut),
        )
        media_base = (settings.MEDIA_URL or '/media/').rstrip('/')
        result['url'] = request.build_absolute_uri(f"{media_base}/{result['path']}")
        return ApiResponseSuccess(result).response()


class SipoCandidatoDocumentoView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request, sip_id, candidato_id, doc_type):
        import mimetypes

        from django.http import FileResponse, Http404, HttpResponseRedirect

        from .models import SipoCandidatoObra

        get_obra_for_user(int(sip_id), request.user)
        key = (doc_type or '').strip().lower()
        if key not in DOC_FIELD_MAP:
            raise Http404

        candidato = (
            SipoCandidatoObra.objects.using('sip_db')
            .filter(
                cf_rrhh_sip_obra_id=int(sip_id),
                cf_rrhh_sip_obra_candidato_id=str(candidato_id),
            )
            .first()
        )
        if candidato is None:
            raise Http404

        field = DOC_FIELD_MAP[key]
        stored = getattr(candidato, field, None)
        if not stored:
            raise Http404

        raw = str(stored).strip()
        if is_external_candidato_doc_url(raw):
            return HttpResponseRedirect(raw)

        local_path = resolve_local_candidato_doc_path(raw)
        if not local_path:
            raise Http404

        content_type = mimetypes.guess_type(local_path)[0] or 'application/octet-stream'
        return FileResponse(
            open(local_path, 'rb'),
            content_type=content_type,
            filename=os.path.basename(local_path),
        )


class SipoCandidatoToggleSeleccionView(APIView):
    permission_classes = [IsSipoAdminOrRrhh]

    def post(self, request, sip_id, candidato_id):
        candidato = toggle_seleccion_candidato(
            sip_id=int(sip_id),
            candidato_id=str(candidato_id),
            user=request.user,
        )
        item = SipoCandidatoSerializer(candidato).data
        return ApiResponseSuccess(item).response()


class SipoCandidatoToggleSeleccionByIdView(APIView):
    permission_classes = [IsSipoAdminOrRrhh]

    def post(self, request, candidato_id):
        from rest_framework import status
        from rest_framework.exceptions import APIException

        from .constants import SIPO_CANDIDATO_ACTIVO
        from .models import SipoCandidatoObra

        row = (
            SipoCandidatoObra.objects.using('sip_db')
            .filter(
                cf_rrhh_sip_obra_candidato_id=str(candidato_id),
                cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
            )
            .first()
        )
        if not row:
            raise APIException('Candidato no encontrado', status.HTTP_400_BAD_REQUEST)
        candidato = toggle_seleccion_candidato(
            sip_id=int(row.cf_rrhh_sip_obra_id),
            candidato_id=str(candidato_id),
            user=request.user,
        )
        item = SipoCandidatoSerializer(candidato).data
        return ApiResponseSuccess(item).response()


class SipoCandidatosSeleccionarTodosView(APIView):
    permission_classes = [IsSipoAdminOrRrhh]

    def post(self, request, sip_id):
        serializer = SipoSeleccionarTodosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = seleccionar_todos_candidatos(
            sip_id=int(sip_id),
            seleccionado=serializer.validated_data['seleccionado'],
            user=request.user,
        )
        return ApiResponseSuccess(result).response()


class SipoSyncSapView(APIView):
    permission_classes = [IsSipoAdminOrRrhh]

    def post(self, request, sip_id):
        result = sync_sipo_candidatos_sap(sip_id=int(sip_id), user=request.user)
        return ApiResponseSuccess(result).response()


class SipoAprobarContratacionView(APIView):
    permission_classes = [IsSipoAdminOrRrhh]

    def post(self, request, sip_id):
        result = aprobar_contratacion_obra(sip_id=int(sip_id), user=request.user)
        obra = get_obra_for_user(int(sip_id), request.user)
        item = SipoObraDetailSerializer(obra, context={'request': request}).data
        return ApiResponseSuccess({**result, 'obra': item}).response()


class SipoCandidatosSeleccionadosView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request, sip_id):
        candidatos = list_candidatos_seleccionados(int(sip_id), request.user)
        items = SipoCandidatoSeleccionadoSerializer(
            candidatos, many=True, context={'request': request}
        ).data
        return ApiResponseSuccess(items).response()


class SipoCandidatoToggleRevisionDtView(APIView):
    permission_classes = [IsSipoAdminOrRrhh]

    def patch(self, request, candidato_id):
        candidato = toggle_revision_dt_candidato(
            candidato_id=str(candidato_id),
            user=request.user,
        )
        item = SipoCandidatoSeleccionadoSerializer(
            candidato, context={'request': request}
        ).data
        return ApiResponseSuccess(item).response()
