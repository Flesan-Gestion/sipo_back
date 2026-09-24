from rest_framework.views import APIView

from utils.responses import ApiResponseSuccess

from .permissions import IsSipoAuthenticated
from .services.maestros import list_centros_costo, list_razones_sociales
from .services.pais_segregation import normalize_pais


class SipoRazonesSocialesView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request):
        pais = normalize_pais(request.query_params.get('external_code_pais'))
        items = list_razones_sociales(external_code_pais=pais)
        return ApiResponseSuccess(items).response()


class SipoCentrosCostoView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request):
        pais = normalize_pais(request.query_params.get('external_code_pais'))
        razon_social_id = (
            request.query_params.get('razon_social_id')
            or request.query_params.get('empresa_rut')
            or request.query_params.get('rut')
            or ''
        ).strip() or None
        items = list_centros_costo(
            external_code_pais=pais,
            razon_social_id=razon_social_id,
        )
        return ApiResponseSuccess(items).response()
