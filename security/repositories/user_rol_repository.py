from django.db.models.base import Model as Model
from utils.repository import EssentialRepository
from ..models import UserRol

class UserRolRepository(EssentialRepository):
    
    def __init__(self):
        super().__init__(UserRol)
        self.connection = "security"
        self.logical_deletion = False