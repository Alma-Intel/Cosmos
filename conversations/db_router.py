"""
Database router for conversations models to use the conversations database
"""
class ConversationsRouter:
    """
    A router to control all database operations on models in the conversations app
    that should use the 'conversations' database.
    """
    
    route_app_labels = {'conversations'}
    conversations_models = {'Conversation', 'Message'}

    def db_for_read(self, model, **hints):
        """Suggest which database to read from."""
        if model._meta.app_label in self.route_app_labels:
            if model.__name__ in self.conversations_models:
                return 'conversations'
        return None

    def db_for_write(self, model, **hints):
        """Suggest which database to write to."""
        if model._meta.app_label in self.route_app_labels:
            if model.__name__ in self.conversations_models:
                return 'conversations'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if models are in the same app or both in conversations DB."""
        db_set = {'conversations', 'default'}
        if (obj1._state.db in db_set and obj2._state.db in db_set):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure that conversations models only appear in the conversations database."""
        if app_label in self.route_app_labels:
            if model_name in self.conversations_models:
                return db == 'conversations'
            else:
                # Other models in conversations app go to default database
                return db == 'default'
        return None

