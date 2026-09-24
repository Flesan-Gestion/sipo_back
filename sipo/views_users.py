from rest_framework.views import APIView

from utils.responses import ApiResponseSuccess

from .permissions import IsSipoAdmin, IsSipoAuthenticated
from .serializers_users import (
    SipoPerfilRolSerializer,
    SipoUsuarioCreateSerializer,
    SipoUsuarioSerializer,
    SipoUsuarioUpdateSerializer,
)
from .services.usuario_scope import get_scope_for_user
from .services.usuarios import (
    create_sipo_usuario,
    delete_sipo_usuario,
    get_sipo_usuario_by_id,
    list_sipo_perfiles_roles,
    list_sipo_usuarios,
    update_sipo_usuario,
)


class SipoUsuariosListCreateView(APIView):
    permission_classes = [IsSipoAdmin]

    def get(self, request):
        search = (request.query_params.get('search') or request.query_params.get('q') or '').strip()
        cf_rol_id_raw = request.query_params.get('cf_rol_id') or request.query_params.get('rol_id')
        cf_rol_id = int(cf_rol_id_raw) if cf_rol_id_raw not in (None, '') else None

        items = list_sipo_usuarios(search=search or None, cf_rol_id=cf_rol_id)
        serializer = SipoUsuarioSerializer(items, many=True)
        return ApiResponseSuccess(serializer.data).response()

    def post(self, request):
        serializer = SipoUsuarioCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        created = create_sipo_usuario(
            correo=data['correo'],
            rol_id=data.get('rol_id') or data.get('cf_rol_id'),
            rol_nombre=data.get('rol_nombre'),
            empresas_ids=data.get('empresas_ids'),
            centros_costo_ids=data.get('centros_costo_ids'),
            empresas_meta=data.get('empresas_meta'),
            centros_meta=data.get('centros_meta'),
        )
        return ApiResponseSuccess(SipoUsuarioSerializer(created).data).response()


class SipoUsuarioDetailView(APIView):
    permission_classes = [IsSipoAdmin]

    def get(self, request, usuario_id: int):
        item = get_sipo_usuario_by_id(usuario_id)
        if item is None:
            from rest_framework.exceptions import NotFound

            raise NotFound('Usuario no encontrado.')
        return ApiResponseSuccess(SipoUsuarioSerializer(item).data).response()

    def patch(self, request, usuario_id: int):
        serializer = SipoUsuarioUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        updated = update_sipo_usuario(
            usuario_id,
            rol_id=data.get('rol_id') or data.get('cf_rol_id'),
            rol_nombre=data.get('rol_nombre'),
            empresas_ids=data.get('empresas_ids'),
            centros_costo_ids=data.get('centros_costo_ids'),
            empresas_meta=data.get('empresas_meta'),
            centros_meta=data.get('centros_meta'),
        )
        return ApiResponseSuccess(SipoUsuarioSerializer(updated).data).response()

    def delete(self, request, usuario_id: int):
        delete_sipo_usuario(usuario_id)
        return ApiResponseSuccess({'id': usuario_id, 'deleted': True}).response()


class SipoPerfilesListView(APIView):
    permission_classes = [IsSipoAdmin]

    def get(self, request):
        roles = list_sipo_perfiles_roles()
        serializer = SipoPerfilRolSerializer(roles, many=True)
        return ApiResponseSuccess(serializer.data).response()


class SipoMiAlcanceView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request):
        return ApiResponseSuccess(get_scope_for_user(request.user)).response()
