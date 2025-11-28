# Generated manually - Set admin user role to Admin

from django.db import migrations
from django.conf import settings


def set_admin_role(apps, schema_editor):
    """Set the admin user's role to Admin"""
    UserProfile = apps.get_model('conversations', 'UserProfile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    
    try:
        admin_user = User.objects.get(username='admin')
        profile, created = UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={'role': 'Admin'}
        )
        if not created:
            profile.role = 'Admin'
            profile.save()
    except User.DoesNotExist:
        # Admin user doesn't exist yet, that's okay
        pass
    except Exception:
        # If there's any error, just continue
        pass


def reverse_set_admin_role(apps, schema_editor):
    """Reverse migration - set admin role back to User"""
    UserProfile = apps.get_model('conversations', 'UserProfile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    
    try:
        admin_user = User.objects.get(username='admin')
        try:
            profile = UserProfile.objects.get(user=admin_user)
            profile.role = 'User'
            profile.save()
        except UserProfile.DoesNotExist:
            pass
    except User.DoesNotExist:
        pass
    except Exception:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('conversations', '0003_add_roles_teams'),
    ]

    operations = [
        migrations.RunPython(set_admin_role, reverse_set_admin_role),
    ]

