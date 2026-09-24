
import math
from dataclasses import dataclass
from typing import List, Optional, Dict, Union, Generic, TypeVar
from django.http import JsonResponse
from .serializers import ApiDataResponseSerializer, ApiGetResponseSerializer,TokenResponseSerializer
from rest_framework.serializers import ReturnDict

T = TypeVar('T')

@dataclass
class Pagination:
    current_page: int
    per_page: int
    total_pages: int
    total_records: int
    next_page_url: Optional[str] = None
    previous_page_url: Optional[str] = None

@dataclass
class Data(Generic[T]):
    count: int
    items: List[T]
    pagination: Optional[Pagination] = None
    
    def __init__(self, items, request = None, total_records = 0):
        self.count = len(items)
        self.items = items
        
        if (request):
            page = int(request.query_params.get("page") or 1)
            per_page = int(
                request.query_params.get("per_page")
                or request.query_params.get("perPage")
                or 10
            )
            total_pages = max(1, math.ceil(total_records / per_page)) if per_page else 1
            next_page_url = request.build_absolute_uri().replace(f"page={page}", f"page={page+1}")
            previous_page_url = request.build_absolute_uri().replace(f"page={page}", f"page={page-1 if page-1 > 0 else 1}")
            
            self.pagination = Pagination(
                page,
                per_page, 
                total_pages,
                total_records,
                next_page_url,
                previous_page_url
            )

@dataclass
class ApiResponse:
    status: int
    detail: str
    data: Optional[Union[ReturnDict, Data]] = None
    def response(self):
        json = self.getSerializable()
            
        return JsonResponse(json.data, safe=False)
    
    def getSerializable(self):
        if isinstance(self.data, Data):
            json = ApiDataResponseSerializer(self)
        else:
            json = ApiGetResponseSerializer(self)
            
        return json
    
@dataclass
class ApiResponseSuccess(ApiResponse):
    def __init__(self, data: Union[Dict, Data]):
        super().__init__(200, "Successful operation", data)
        
@dataclass
class ApiResponseError(ApiResponse):
    def __init__(self, status = 400, detail = None):
        super().__init__(status, detail)