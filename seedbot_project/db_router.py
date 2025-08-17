class SeedBotRouter:
    def _is_presets_app_model(self, model_name):
        # All models related to the app's core data
        return model_name in ['preset', 'userpermission', 'seedlog', 'featurepreset']

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'presets':
            if self._is_presets_app_model(model._meta.model_name):
                return 'seedbot_db'
            return 'default' # For any other model in this app
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'presets':
            if self._is_presets_app_model(model._meta.model_name):
                return 'seedbot_db'
            return 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations between the two databases
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'presets':
            if self._is_presets_app_model(model_name):
                return db == 'seedbot_db'
            return db == 'default' # For other models
        
        # Only allow non-presets app migrations on the default DB
        elif db == 'default':
             return True
        return None