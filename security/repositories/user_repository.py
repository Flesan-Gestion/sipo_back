import logging
import os

from utils.repository import EssentialRepository
from ..models import User

logger = logging.getLogger(__name__)


class UserRepository(EssentialRepository):

    def __init__(self):
        super().__init__(User)
        self.connection = "security"
        self.logical_deletion = False

    def get_by_username(self, username: str):
        normalized_username = (username or '').strip().lower()
        if not normalized_username:
            return None

        try:
            return (
                User.objects.using(self.connection)
                .filter(
                    id_aplicacion=os.getenv('ID_APP'),
                    username=normalized_username,
                )
                .prefetch_related('roles', 'roles__rol')
                .first()
            )
        except Exception:
            logger.exception('Error al consultar usuario username=%s', normalized_username)
            return None
