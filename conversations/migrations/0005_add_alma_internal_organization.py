# Generated migration for adding alma_internal_organization field to UserProfile and Team

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conversations', '0004_set_admin_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='alma_internal_organization',
            field=models.CharField(blank=True, help_text='Internal Organization - only visible to admins', max_length=255, null=True, verbose_name='ALMA Internal Organization'),
        ),
        migrations.AddField(
            model_name='team',
            name='alma_internal_organization',
            field=models.CharField(blank=True, help_text='Internal Organization - only visible to admins', max_length=255, null=True, verbose_name='ALMA Internal Organization'),
        ),
    ]

