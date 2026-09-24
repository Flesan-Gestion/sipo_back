class SipoObraRouter:
    """Rutas DB: modelos legado SIP → sip_db; ficha/historial → default."""

    sip_obra_models = {
        'siporol',
        'sipoperfil',
        'sipoobra',
        'sapmaestroempresadepuncc',
        'sipoobracargo',
    }

    default_models = {
        'sipofichaingreso',
        'siposolicitudhistorial',
    }

    def db_for_read(self, model, **hints):
        name = model._meta.model_name
        if name in self.default_models:
            return 'default'
        if name in self.sip_obra_models:
            return 'sip_db'
        if model._meta.app_label == 'sipo':
            return 'sip_db'
        return None

    def db_for_write(self, model, **hints):
        name = model._meta.model_name
        if name in self.default_models:
            return 'default'
        if name in self.sip_obra_models:
            return 'sip_db'
        if model._meta.app_label == 'sipo':
            return 'sip_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (
            obj1._meta.model_name in self.sip_obra_models
            or obj2._meta.model_name in self.sip_obra_models
            or obj1._meta.model_name in self.default_models
            or obj2._meta.model_name in self.default_models
            or obj1._meta.app_label == 'sipo'
            or obj2._meta.app_label == 'sipo'
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if model_name in self.default_models:
            return db == 'default'
        if app_label == 'sipo' or model_name in self.sip_obra_models:
            return False
        return db == 'default'
