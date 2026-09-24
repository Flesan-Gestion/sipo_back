from rest_framework.views import APIView

from utils.responses import ApiResponseSuccess

from .permissions import IsSipoAdmin
from .serializers_cargos_horarios import (
    SipoConfigCargoAssignSerializer,
    SipoConfigCargoToggleSerializer,
    SipoConfigHorarioAssignSerializer,
    SipoConfigHorarioDeleteSerializer,
)
from .services.cargos_horarios import (
    assign_cargo_empresa,
    assign_horario_empresa,
    delete_horario_empresa,
    list_cargos_catalogo_sap,
    list_cargos_empresa,
    list_empresas_config,
    list_horarios_catalogo_sap,
    list_horarios_empresa,
    set_cargo_activo,
)


class SipoConfigEmpresasView(APIView):
    permission_classes = [IsSipoAdmin]

    def get(self, request):
        return ApiResponseSuccess(list_empresas_config()).response()


class SipoConfigCargosView(APIView):
    permission_classes = [IsSipoAdmin]

    def get(self, request):
        empresa_id = request.query_params.get('empresa_id')
        if not empresa_id:
            return ApiResponseSuccess({'catalogo': list_cargos_catalogo_sap()}).response()
        return ApiResponseSuccess(
            {
                'cargos': list_cargos_empresa(empresa_id),
                'catalogo': list_cargos_catalogo_sap(),
            }
        ).response()

    def post(self, request):
        serializer = SipoConfigCargoAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        item = assign_cargo_empresa(
            empresa_id=data['empresa_id'],
            external_code=data['external_code'],
            nombre=data.get('nombre'),
            area_personal=data.get('area_personal'),
        )
        return ApiResponseSuccess(item).response()

    def put(self, request):
        serializer = SipoConfigCargoToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        set_cargo_activo(
            empresa_id=data['empresa_id'],
            cargo_id=data.get('id'),
            nombre=data.get('nombre'),
            activo=data['activo'],
        )
        return ApiResponseSuccess({'ok': True}).response()


class SipoConfigHorariosView(APIView):
    permission_classes = [IsSipoAdmin]

    def get(self, request):
        empresa_id = request.query_params.get('empresa_id')
        if not empresa_id:
            return ApiResponseSuccess({'catalogo': list_horarios_catalogo_sap()}).response()
        return ApiResponseSuccess(
            {
                'horarios': list_horarios_empresa(empresa_id),
                'catalogo': list_horarios_catalogo_sap(),
            }
        ).response()

    def post(self, request):
        serializer = SipoConfigHorarioAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        item = assign_horario_empresa(
            empresa_id=data['empresa_id'],
            external_code=data['external_code'],
            descripcion=data.get('descripcion'),
        )
        return ApiResponseSuccess(item).response()

    def put(self, request):
        serializer = SipoConfigHorarioDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        delete_horario_empresa(
            empresa_id=data['empresa_id'],
            external_code=data['external_code'],
        )
        return ApiResponseSuccess({'ok': True}).response()
