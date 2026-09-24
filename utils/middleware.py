from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from .responses import ApiResponseError
import json


class ErrorHandlerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            json_content = response.content.decode('utf-8')
            data = json.loads(json_content)
            response.status_code = data["status"]
            return response
        except Exception:
            return response

    def process_exception(self, request, exception):
        error_detail = str(exception)
        return ApiResponseError(500, detail=error_detail).response()


def ErrorApiHandlerMiddleware(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, APIException):
        detail = exc.detail
        status_code = response.status_code or 400
        if isinstance(detail, (dict, list)):
            payload = ApiResponseError(
                status_code,
                'Error de validación: complete los campos obligatorios.',
            ).getSerializable().data
            payload['data'] = detail
            response.data = payload
            response.status_code = status_code
        elif hasattr(detail, 'code'):
            try:
                code = int(detail.code)
            except (TypeError, ValueError):
                code = status_code
            response.data = ApiResponseError(code, str(detail)).getSerializable().data
            response.status_code = code
        else:
            response.data = ApiResponseError(status_code, str(detail)).getSerializable().data
            response.status_code = status_code
    return response
