import mimetypes
import os

from django.http import FileResponse, Http404, HttpResponse
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from utils.responses import ApiResponseSuccess

from .constants import SIPO_ROL_SUPERVISOR
from .permissions import IsSipoAuthenticated
from .serializers_ficha import (
    SipoFichaIngresoDetailSerializer,
    SipoFichaIngresoListSerializer,
    SipoFichaIngresoWriteSerializer,
    SipoFichaRsCcWriteSerializer,
)
from .services.fichas import (
    aprobar_ficha,
    create_ficha,
    eliminar_ficha,
    ficha_es_editable,
    get_ficha_for_user,
    list_fichas,
    rechazar_ficha,
    retroceder_ficha,
    update_ficha,
)
from .services.pdf_ficha import build_ficha_pdf

FICHA_DOC_FIELDS = {
    'domicilio': 'doc_domicilio',
    'titulo': 'doc_titulo',
    'afp': 'doc_afp',
    'salud': 'doc_salud',
    'cedula': 'doc_cedula',
}

FICHA_REQUIRED_DOCS = (
    ('doc_domicilio', 'comprobanteDomicilio'),
    ('doc_afp', 'certificadoAfp'),
    ('doc_salud', 'certificadoSalud'),
    ('doc_cedula', 'copiaCedula'),
)


def _multipart_data(request) -> dict:
    data = {key: request.data.get(key) for key in request.data.keys()}
    if hasattr(request.data, 'lists'):
        data = {
            key: (values[0] if len(values) == 1 else values)
            for key, values in request.data.lists()
        }
    return data


def _assert_ficha_docs_present(*, files, ficha=None) -> None:
    from rest_framework.exceptions import ValidationError

    errors = {}
    for field, alt in FICHA_REQUIRED_DOCS:
        uploaded = (files.get(field) if files else None) or (
            files.get(alt) if files else None
        )
        existing = getattr(ficha, field, None) if ficha is not None else None
        if not uploaded and not existing:
            errors[field] = ['Documento obligatorio.']
    if errors:
        raise ValidationError(errors)


class SipoFichasListCreateView(APIView):
    permission_classes = [IsSipoAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        search = (request.query_params.get('search') or request.query_params.get('q') or '').strip()
        solo_aprobadas = str(request.query_params.get('aprobadas') or '').lower() in (
            '1',
            'true',
            'yes',
        )
        razon_social_id = (
            request.query_params.get('razon_social_id')
            or request.query_params.get('empresa_rut')
            or ''
        ).strip() or None
        items = list_fichas(
            user=request.user,
            search=search or None,
            solo_aprobadas=solo_aprobadas,
            razon_social_id=razon_social_id,
        )
        data = SipoFichaIngresoListSerializer(
            items, many=True, context={'request': request}
        ).data
        return ApiResponseSuccess(data).response()

    def post(self, request):
        data = _multipart_data(request)
        solo_rrhh = str(data.get('solo_rrhh') or '').lower() in ('1', 'true', 'si')
        solo_supervisor = str(data.get('solo_supervisor') or '').lower() in ('1', 'true', 'si')
        if int(getattr(request.user, 'sip_rol_id', -1) or -1) == SIPO_ROL_SUPERVISOR:
            solo_supervisor = True
            data = {**data, 'solo_supervisor': '1'}
        rs_cc = SipoFichaRsCcWriteSerializer(data=data)
        rs_cc.is_valid(raise_exception=True)
        write_ser = SipoFichaIngresoWriteSerializer(
            data=data,
            context={'solo_rrhh': solo_rrhh, 'solo_supervisor': solo_supervisor},
        )
        write_ser.is_valid(raise_exception=True)
        files = request.FILES
        if not solo_rrhh and not solo_supervisor:
            _assert_ficha_docs_present(files=files, ficha=None)
        ficha = create_ficha(data=data, files=files, user=request.user)
        payload = SipoFichaIngresoDetailSerializer(ficha, context={'request': request}).data
        return ApiResponseSuccess(payload).response()


class SipoFichaDetailView(APIView):
    permission_classes = [IsSipoAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, ficha_id: int):
        ficha = get_ficha_for_user(ficha_id, request.user)
        payload = SipoFichaIngresoDetailSerializer(ficha, context={'request': request}).data
        return ApiResponseSuccess(payload).response()

    def patch(self, request, ficha_id: int):
        data = _multipart_data(request)
        ficha = get_ficha_for_user(ficha_id, request.user)
        if not ficha_es_editable(ficha):
            raise APIException(
                'La ficha no puede modificarse porque ya fue aprobada o finalizada.',
                status.HTTP_400_BAD_REQUEST,
            )
        if any(k in data for k in ('razon_social_id', 'centro_costo_id', 'external_code_pais')):
            serializer = SipoFichaRsCcWriteSerializer(
                data=data,
                partial=True,
                context={'ficha': ficha},
            )
            serializer.is_valid(raise_exception=True)
        files = request.FILES
        solo_rrhh = str(data.get('solo_rrhh') or '').lower() in ('1', 'true', 'si')
        solo_supervisor = str(data.get('solo_supervisor') or '').lower() in ('1', 'true', 'si')
        if int(getattr(request.user, 'sip_rol_id', -1) or -1) == SIPO_ROL_SUPERVISOR:
            solo_supervisor = True
            data = {**data, 'solo_supervisor': '1'}
        if solo_supervisor or solo_rrhh or 'rut' in data or 'nombres' in data:
            write_ser = SipoFichaIngresoWriteSerializer(
                data=data,
                context={'solo_rrhh': solo_rrhh, 'solo_supervisor': solo_supervisor},
            )
            write_ser.is_valid(raise_exception=True)
            if not solo_rrhh and not solo_supervisor:
                _assert_ficha_docs_present(files=files, ficha=ficha)
        ficha = update_ficha(
            ficha_id=ficha_id,
            data=data,
            files=files,
            user=request.user,
        )
        payload = SipoFichaIngresoDetailSerializer(ficha, context={'request': request}).data
        return ApiResponseSuccess(payload).response()

    def delete(self, request, ficha_id: int):
        result = eliminar_ficha(ficha_id=ficha_id, user=request.user)
        return ApiResponseSuccess(result).response()


class SipoFichaAccesoView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def post(self, request, ficha_id: int):
        get_ficha_for_user(ficha_id, request.user)
        origin = request.headers.get('Origin') or 'http://localhost:5173'
        from .services.ficha_portal import emitir_acceso_ficha
        return ApiResponseSuccess(
            emitir_acceso_ficha(ficha_id=ficha_id, front_origin=origin)
        ).response()


class SipoFichaPdfView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request, ficha_id: int):
        ficha = get_ficha_for_user(ficha_id, request.user)
        pdf_bytes = build_ficha_pdf(ficha)
        rut_safe = ''.join(ch for ch in str(ficha.rut or 'sinrut') if ch.isalnum() or ch in '-_')
        filename = f'Ficha_Ingreso_{rut_safe}.pdf'
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class SipoFichaAdjuntoView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request, ficha_id: int, doc_type: str):
        ficha = get_ficha_for_user(ficha_id, request.user)
        field_name = FICHA_DOC_FIELDS.get((doc_type or '').strip().lower())
        if not field_name:
            raise Http404
        field = getattr(ficha, field_name, None)
        if not field:
            raise Http404
        try:
            path = field.path
        except (ValueError, FileNotFoundError) as exc:
            raise Http404 from exc
        if not path or not os.path.isfile(path):
            raise Http404
        content_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        return FileResponse(
            open(path, 'rb'),
            content_type=content_type,
            filename=os.path.basename(path),
        )


class SipoFichaAprobarView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def post(self, request, ficha_id: int):
        ficha = aprobar_ficha(ficha_id=ficha_id, user=request.user)
        payload = SipoFichaIngresoDetailSerializer(ficha, context={'request': request}).data
        return ApiResponseSuccess(payload).response()


class SipoFichaRechazarView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def post(self, request, ficha_id: int):
        comentario = (
            request.data.get('comentario')
            or request.data.get('motivo')
            or request.data.get('observacion')
            or ''
        )
        ficha = rechazar_ficha(
            ficha_id=ficha_id,
            user=request.user,
            comentario=comentario,
        )
        payload = SipoFichaIngresoDetailSerializer(ficha, context={'request': request}).data
        return ApiResponseSuccess(payload).response()


class SipoFichaRetrocederView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def post(self, request, ficha_id: int):
        ficha = retroceder_ficha(ficha_id=ficha_id, user=request.user)
        payload = SipoFichaIngresoDetailSerializer(ficha, context={'request': request}).data
        return ApiResponseSuccess(payload).response()
