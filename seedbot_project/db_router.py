class SeedBotRouter:
    """
    A router to control all database operations on models in the
    presets application.
    """
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'presets':
            if model._meta.model_name in ['preset', 'userpermission']:
                return 'seedbot_db'
            else:
                return 'default'
        
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'presets':
            if model._meta.model_name in ['preset', 'userpermission']:
                return 'seedbot_db'
            else:
                return 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'presets':
            if model_name in ['preset', 'userpermission']:
                return db == 'seedbot_db'
            else:
                return db == 'default'
        
        return db == 'default'