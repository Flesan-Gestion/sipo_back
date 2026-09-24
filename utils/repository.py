from django.db import models
from django.db.models import Q
import json

class EssentialRepository():
    
    def __init__(self, model: models.Model, logical_deletion = False, connection = 'default'):
        self.model = model
        self.logical_deletion = logical_deletion
        self.connection = connection
        
    def count(self):
        return self.model.objects.all().count()
        
    # Obtener datos. Filtros y ordenamiento opcional.
    def get(self, relations=[], filters={}, orderBy=[]):
        if self.logical_deletion: filters.update({'enable': 1})
        querySet = self.model.objects.using(self.connection)
        if len(relations) > 0: querySet = querySet.select_related(*relations)
        if len(orderBy) > 0: querySet = querySet.order_by(*orderBy)    
        if filters: querySet = querySet.filter(**filters)
        return querySet
    
    # Obtener datos con filtros de tipo query (uso del modelo Q de django)
    def getWithQuery(self, relations=[], filters=Q(), orderBy=[]):
        if self.logical_deletion: filters &= Q(enable=1)
        querySet = self.model.objects.using(self.connection)
        if len(relations) > 0: querySet = querySet.select_related(*relations)
        if len(orderBy) > 0: querySet = querySet.order_by(*orderBy)    
        if filters: querySet = querySet.filter(filters)
        return querySet

    # Obtener un registro a través de filtros.
    def getByFilters(self, relations = [], filters={}, orderBy=[]):
        if self.logical_deletion: filters.update({'enable': 1})
        querySet = self.model.objects.using(self.connection)
        if len(relations) > 0: querySet = querySet.select_related(*relations)
        if len(orderBy) > 0: querySet = querySet.order_by(*orderBy)    
        if filters: querySet = querySet.filter(**filters)
        return querySet.first()

    # Obtener por id
    def getById(self, pk, relations = []):
        filters = {'pk': pk}
        if self.logical_deletion: filters.update({'enable': 1})
        querySet = self.model.objects.using(self.connection)
        if len(relations) > 0:
            querySet = querySet.select_related(*relations)
        return querySet.filter(**filters).first()
    
    # Guardar en base de datos
    def create(self, payload):
        result = self.model.objects.using(self.connection).create(**payload)
        return result
    
    # Actualizar en base de datos
    def update(self, pk, payload):
        data = self.get(filters={pk: pk})
        if len(data) == 0 : return None
        data.update(**payload)
        result = self.getById(pk)
        return result
    
    # Inhabilitar. Solo funciona para modelos que tienen eliminación lógica.
    def disable(self, pk):
        data = self.get(filters={pk: pk})
        if len(data) == 0 : return None
        data.update(enable=0)
        return 1

    # Eliminar registro. No recomendable usar.
    def delete(self, pk):
        data = self.get(filters={pk: pk})
        result = data.delete()
        return result
    
	# Construir filtros en base a los parámetros de peticiones con lazy loading
    def buildLazyFilters(self, request):

        filterText = request.query_params.get("filterText")
        filterFields = request.query_params.get("filterFields")
        matchingFilters = request.query_params.get("matchingFilters")
        
        filters = Q()

        fields = ("" if filterFields is None else filterFields).split(",")
        
        if filterText:
            optionalFilters = Q()
            for field in fields:
                optionalFilters |= Q(**{f"{field}__icontains":filterText})
            filters &= optionalFilters

        if (matchingFilters is not None):
            for field in json.loads(matchingFilters):
                filters &= Q(**{f"{field}":json.loads(matchingFilters)[field]})
        
        return filters
    
	# Construir el orderBy en base a los parámetros de peticiones con lazy loading
    def buildLazyOrder(self, request):
        orderBy = request.query_params.get("orderBy")
        order = [] if orderBy is None else orderBy.split(",")
        return order
    
	# Construir el orderBy en base a los parámetros de peticiones con lazy loading
    def buildLazyRecords(self, request, querySet):
        page = int(request.query_params.get("page"))
        perPage = int(request.query_params.get("perPage"))
        
        startRowNumber = perPage*(page-1)
        endRowNumber = startRowNumber + perPage
        records = querySet[startRowNumber:endRowNumber]
        return records