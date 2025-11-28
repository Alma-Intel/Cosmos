# Generated manually to fix missing table issue

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('conversations', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS conversations_userprofile (
                id BIGSERIAL PRIMARY KEY,
                external_uuid VARCHAR(255),
                cell_phone VARCHAR(20),
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                user_id INTEGER NOT NULL UNIQUE REFERENCES auth_user(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS conversations_userprofile_user_id_idx ON conversations_userprofile(user_id);
            """,
            reverse_sql="DROP TABLE IF EXISTS conversations_userprofile;",
        ),
    ]

