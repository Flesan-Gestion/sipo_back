class SipSessionUser:
    is_active = True
    is_staff = False
    is_superuser = False

    def __init__(
        self,
        *,
        email: str,
        sip_rol_id: int,
        first_name: str = '',
        last_name: str = '',
    ):
        self.email = email
        self.username = email
        self.sip_rol_id = int(sip_rol_id)
        self.first_name = first_name
        self.last_name = last_name
        self.pk = None
        self.id = None

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_username(self) -> str:
        return self.username

    def __str__(self) -> str:
        return self.email

    @classmethod
    def from_token(cls, validated_token) -> 'SipSessionUser':
        user_data = validated_token.get('user') or {}
        email = (
            user_data.get('username')
            or validated_token.get('email')
            or ''
        ).strip().lower()
        sip_rol_id = int(
            validated_token.get('sip_rol_id')
            if validated_token.get('sip_rol_id') is not None
            else user_data.get('sip_rol_id')
            if user_data.get('sip_rol_id') is not None
            else -1
        )
        if not email or sip_rol_id < 0:
            raise ValueError('Token SIPO inválido: falta email o rol.')

        return cls(
            email=email,
            sip_rol_id=sip_rol_id,
            first_name=user_data.get('nombres') or '',
            last_name=user_data.get('apellidos') or '',
        )
