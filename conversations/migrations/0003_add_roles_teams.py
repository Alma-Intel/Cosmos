# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('conversations', '0002_create_userprofile_table'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True, verbose_name='Team Name')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Team',
                'verbose_name_plural': 'Teams',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='userprofile',
            name='role',
            field=models.CharField(
                choices=[('User', 'User'), ('Manager', 'Manager'), ('Director', 'Director'), ('Admin', 'Admin')],
                default='User',
                max_length=20,
                verbose_name='Role'
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='team',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='members',
                to='conversations.team',
                verbose_name='Team'
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='alma_internal_uuid',
            field=models.CharField(
                blank=True,
                help_text='Internal UUID - only visible to admins',
                max_length=255,
                null=True,
                verbose_name='ALMA Internal UUID'
            ),
        ),
    ]

