from django.apps import AppConfig


class ConversationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'conversations'
    
    def ready(self):
        """Load UUID to email mapping at startup"""
        # Import here to avoid circular imports
        from .mongodb import get_uuid_to_email_mapping
        from django.conf import settings
        
        if settings.DEBUG:
            print("Loading UUID to email mapping at startup...")
        # Pre-load the mapping
        get_uuid_to_email_mapping()

