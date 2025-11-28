"""
Custom authentication backend for single admin user
"""
from django.contrib.auth.models import User
from django.contrib.auth.backends import BaseBackend
from django.conf import settings
import hashlib


class SingleAdminBackend(BaseBackend):
    """
    Custom authentication backend that allows a single hardcoded admin user.
    Username: admin
    Password: (stored as hash in settings)
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Only authenticate 'admin' user
        if username != 'admin':
            return None
        
        # Get the password hash from settings
        admin_password_hash = getattr(settings, 'ADMIN_PASSWORD_HASH', None)
        
        if not admin_password_hash:
            return None
        
        # Hash the provided password and compare
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if password_hash == admin_password_hash:
            # Get or create the admin user
            user, created = User.objects.get_or_create(
                username='admin',
                defaults={
                    'is_staff': True,
                    'is_superuser': True,
                    'is_active': True,
                }
            )
            if created:
                # Set a random password in the database (won't be used, but good practice)
                user.set_unusable_password()
                user.save()
            return user
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

