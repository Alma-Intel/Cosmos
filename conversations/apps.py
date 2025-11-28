from django.apps import AppConfig


class ConversationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'conversations'
    
    def ready(self):
        """Load UUID to email mapping at startup (don't load filter options - too slow)"""
        # Import here to avoid circular imports
        from .mongodb import get_uuid_to_email_mapping
        from django.conf import settings
        
        if settings.DEBUG:
            print("Loading UUID to email mapping at startup...")
        # Pre-load the mapping (this is fast)
        try:
            get_uuid_to_email_mapping()
        except Exception as e:
            if settings.DEBUG:
                print(f"Warning: Could not load UUID mapping at startup: {e}")
        # Don't pre-load sellers/tags/stages - they're too slow and will be cached on first use

