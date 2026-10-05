from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from utils.responses import ApiResponseSuccess

from .permissions import IsSipoAuthenticated
from .services.candidato_portal import emitir_acceso
from .services.ficha_portal import guardar_ficha_publica, resumen_ficha


class SipoCandidatoAccesoView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def post(self, request, sip_id, candidato_id):
        origin = (
            request.headers.get('Origin')
            or request.query_params.get('origin')
            or 'http://localhost:5173'
        )
        data = emitir_acceso(
            sip_id=int(sip_id),
            candidato_id=str(candidato_id),
            front_origin=origin,
        )
        return ApiResponseSuccess(data).response()


class SipoPortalCandidatoView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, token):
        return ApiResponseSuccess(resumen_ficha(str(token))).response()

    def post(self, request, token):
        data = {k: request.data.get(k) for k in request.data}
        result = guardar_ficha_publica(token=str(token), data=data, files=request.FILES)
        return ApiResponseSuccess(result).response()
