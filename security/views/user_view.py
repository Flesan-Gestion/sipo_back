from rest_framework.viewsets import ViewSet
from ..repositories.user_repository import UserRepository
from ..repositories.user_rol_repository import UserRolRepository
from rest_framework.decorators import action
from ..serializers import UserSerializer
from utils.responses import ApiResponseSuccess, Data
from ..permissions import TokenAuth
from django.contrib.auth.hashers import make_password
from ..decorators import role_required, scoped_token
import os
from rest_framework.exceptions import APIException
from rest_framework import status
from django.db.models import Q


class UserView(ViewSet):
    
    # Protege la clase validando el Token.
    # permission_classes = [TokenAuth]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repository = UserRepository()
        self.repositoryUserRol = UserRolRepository()
        
    
    @action(methods=["GET"], detail=True)
    def getById(self, request, pk=None):
        user = self.repository.getById(pk=pk)
        # La excepción lanzada de esta forma hará que se formatee una respuesta con el código que ingresas como parámetro.
        if user is None: raise APIException("User not found", status.HTTP_400_BAD_REQUEST)
        item = UserSerializer(user, relations=["roles"]).data
        return ApiResponseSuccess(item).response()
    
    # Forma de proteger una ruta por el rol del usuario
    # @role_required([os.getenv("ROL_PERFIL01")])
    @action(methods=["GET"], detail=False)
    # ESTE ES UN EJEMPLO DE GET DATA USANDO PAGINACIÓN CON FILTROS
    def getData(self, request):
        # PARÁMETROS NECESARIOS PARA LA PAGINACIÓN CON FILTROS Y SUS DEFINICIONES
        # 1. page (obligatorio): Es el número de la página en la que quieres buscar información
        # 2. perPage (obligatorio): La cantidad de registros por páginas que quieres ver
        # 3. filterText (opcional): Es el texto por el cual el usuario buscará
        # 4. filterFields (opcional): Son los campos en los cuales se buscará el texto colocado en filterText
        # 5. matchingFilters (opcional): Es un texto que contiene un json con los filtros. Ejm: "{name: 'Sebastian', ...}"
        # 6. orderBy (opcional): Un texto de campos por los cuales se ordenará separado por comas. Ejm: "name,-created_at,updated_at...". El guión al inicio en caso sea descendente el ordenamiento

		# Construcción de los filtros en base a los parámetros en el request
        filters = self.repository.buildLazyFilters(request)
        
		# Construcción del ordenamiento en base a los parámetros en el request
        order = self.repository.buildLazyOrder(request)

		# Este es un filtro adicional obligatorio solo porque este es el módulo de usuarios y requerimos que traigan los usuarios de este aplicativo en específico.
        filters &= Q(**{"id_aplicacion": os.getenv("ID_APP")})

        # Necesario especificar los roles en las relaciones si vas a mostrarlo en el json para precargar esta información de forma optimizada
        querySet = self.repository.getWithQuery(relations=["roles"], filters=filters, orderBy=order)
        
		# Construyendo la información que enviaremos al serializer
        records = self.repository.buildLazyRecords(request, querySet)
        
        # Serializamos el resultado
        items = UserSerializer(records, relations=["roles"], many=True).data
        
        # Formateamos a modo de data. El especificar los parámetros request y total_records hará que se agregue los campos relacionados a paginación en la respuesta.
        data = Data(items, request, querySet.count())
        return ApiResponseSuccess(data).response()
    
    @action(methods=["GET"], detail=False)
    # ESTE ES UN EJEMPLO DE GET DATA QUE TRAE TODA LA INFORMACIÓN
    def getAllData(self, request):
        querySet = self.repository.get(filters={"id_aplicacion": os.getenv("ID_APP")})
        items = UserSerializer(querySet, relations=["roles"], many=True).data
        data = Data(items)
        return ApiResponseSuccess(data).response()
    
    # Acepta tokens focalizados y de un solo uso
    # @scoped_token()
    # Forma de proteger una ruta por el rol del usuario
    # @role_required([os.getenv("ROL_PERFIL01")])
    @action(methods=["POST"], detail=False)
    def save(self, request):
        user = request.data
        rol = user["rol"]
        del user["rol"]
        
        user["id_aplicacion"] = os.getenv("ID_APP")
        user["password"] = make_password(user["password"])
        
        userCreated = self.repository.create(user)
        rol["aplicacion_usuario"] = userCreated
        self.repositoryUserRol.create(rol)
        
        item = UserSerializer(userCreated).data
        return ApiResponseSuccess(item).response()
    
	# EJEMPLO DE GUARDADO SIMPLE, ESTE NO FUNCIONARÁ PARA ESTA VISTA
    @action(methods=["POST"], detail=False)
    def simpleSave(self, request):
        data = request.data
        ticketCreated = self.repository.create(data)
        item = UserSerializer(ticketCreated).data
        return ApiResponseSuccess(item).response()
    
	# EJEMPLO DE EDICIÓN SIMPLE, ESTE NO FUNCIONARÁ PARA ESTA VISTA
    @action(methods=["POST"], detail=True)
    def simpleEdit(self, request, pk):
        data = request.data
        dataUpdated = self.repository.update(pk, data)
        item = UserSerializer(dataUpdated).data
        return ApiResponseSuccess(item).response()
    
	# EJEMPLO DE DESHABILITAR (ESTO SOLO TENIENDO EN CUENTA EL CAMPO PARA INHABILITAR SEA ENABLE)
    @action(methods=["PUT"], detail=True)
    def disable(self, request, pk=None):
        self.repository.disable(pk)
        return ApiResponseSuccess(None).response()
    
	# EJEMPLO DE HABILITAR (ESTO TENIENDO EN CUENTA QUE EL CAMPO NO SE LLAMA ENABLE)
    @action(methods=["PUT"], detail=True)
    def enable(self, request, pk=None):
        self.repository.update(pk, {"estado": 1})
        return ApiResponseSuccess(None).response()