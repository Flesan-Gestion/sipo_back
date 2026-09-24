from django.http import HttpResponse
from rest_framework.views import APIView

from .permissions import IsSipoAuthenticated
from .services.excel_export import generar_excel_obras, parse_export_filtros


class SipoExportarExcelView(APIView):
    permission_classes = [IsSipoAuthenticated]

    def get(self, request):
        filtros = parse_export_filtros(request)
        buffer = generar_excel_obras(filtros)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="Reporte_SIPO_Obra.xlsx"'
        return response
