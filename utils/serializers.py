from rest_framework import serializers
from rest_framework.fields import SkipField
from rest_framework.relations import PKOnlyObject 
from rest_framework.serializers import ListSerializer

class DynamicFieldsSerializer(serializers.Serializer):
    def to_representation(self, instance):
        ret = {}
        for key, value in instance.items():
            ret[key] = value
        return ret
    
class PaginationSerializer(serializers.Serializer):
    current_page = serializers.IntegerField()
    per_page = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    total_records = serializers.IntegerField()
    next_page_url = serializers.CharField(allow_null=True, allow_blank=True)
    previous_page_url = serializers.CharField(allow_null=True, allow_blank=True)

class DataSerializer(serializers.Serializer):
    count = serializers.IntegerField(required=False)
    items = serializers.ListField(child=serializers.JSONField())  # items puede ser cualquier tipo serializable a JSON
    pagination = PaginationSerializer(required=False)

class ApiDataResponseSerializer(serializers.Serializer):
    status = serializers.IntegerField()
    detail = serializers.CharField()
    data = DataSerializer()
    
class ApiGetResponseSerializer(serializers.Serializer):
    status = serializers.IntegerField()
    detail = serializers.CharField()
    data = serializers.JSONField()

    
class TokenResponseSerializer(serializers.Serializer):
    status = serializers.IntegerField()
    detail = serializers.CharField()
    token = serializers.CharField()
    

class EssentialSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        # Obtener fields de los argumentos por clave
        fields = kwargs.pop('fields', None)
        exclude = kwargs.pop('exclude', None)
        
        # Obtener fields de los argumentos por clave
        relations = kwargs.pop('relations', [])
        # Llamar a la inicialización base del Serializer
        super().__init__(*args, **kwargs)
        
        if fields is not None and exclude is None:
            # Eliminar campos no especificados en fields
            allowed = set(fields)

            existing = set(self.fields)
            
            for field_name in existing - allowed:
                if not(isinstance(self.fields[field_name], EssentialSerializer)):
                    self.fields.pop(field_name)
        
        if exclude is not None and fields is None:
            # Eliminar campos no especificados en fields
            restricted = set(exclude)
            
            for field_name in restricted:
                if not(isinstance(self.fields[field_name], EssentialSerializer)):
                    self.fields.pop(field_name)
            
        existing = set(self.fields)
        for field_name in existing:
            if (isinstance(self.fields[field_name], EssentialSerializer) or isinstance(self.fields[field_name], ListSerializer)) and field_name not in relations:
                self.fields.pop(field_name)
            