# Generated migration to convert Team and UserProfile primary keys to UUIDs

import uuid
from django.db import migrations, models
import django.db.models.deletion


def generate_uuids_for_teams(apps, schema_editor):
    """Generate UUIDs for existing teams"""
    Team = apps.get_model('conversations', 'Team')
    for team in Team.objects.all():
        if not hasattr(team, 'uuid_id') or not team.uuid_id:
            team.uuid_id = uuid.uuid4()
            team.save(update_fields=['uuid_id'])


def generate_uuids_for_profiles(apps, schema_editor):
    """Generate UUIDs for existing user profiles"""
    UserProfile = apps.get_model('conversations', 'UserProfile')
    for profile in UserProfile.objects.all():
        if not hasattr(profile, 'uuid_id') or not profile.uuid_id:
            profile.uuid_id = uuid.uuid4()
            profile.save(update_fields=['uuid_id'])


def update_team_foreign_keys_forward(apps, schema_editor):
    """Update foreign key references to use UUIDs"""
    UserProfile = apps.get_model('conversations', 'UserProfile')
    Team = apps.get_model('conversations', 'Team')
    
    # Create a mapping of old integer IDs to new UUIDs
    # At this point, teams still have both 'id' (integer) and 'uuid_id' (UUID)
    team_id_to_uuid = {}
    for team in Team.objects.all():
        # Access the old integer ID via the database directly
        # The team.id at this point is still the integer primary key
        old_id = team.pk  # This will be the integer ID
        if hasattr(team, 'uuid_id') and team.uuid_id:
            team_id_to_uuid[old_id] = team.uuid_id
    
    # Update UserProfile team references
    # At this point, profile.team is still a ForeignKey to the integer ID
    for profile in UserProfile.objects.exclude(team__isnull=True):
        old_team_id = profile.team_id  # This is the integer foreign key
        if old_team_id and old_team_id in team_id_to_uuid:
            # Set the UUID reference
            profile.team_uuid = team_id_to_uuid[old_team_id]
            profile.save(update_fields=['team_uuid'])


def update_team_foreign_keys_reverse(apps, schema_editor):
    """Reverse migration - not implemented"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('conversations', '0005_add_alma_internal_organization'),
    ]

    operations = [
        # Step 1: Add UUID fields as nullable
        migrations.AddField(
            model_name='team',
            name='uuid_id',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='uuid_id',
            field=models.UUIDField(null=True, editable=False),
        ),
        
        # Step 2: Generate UUIDs for existing records
        migrations.RunPython(generate_uuids_for_teams, migrations.RunPython.noop),
        migrations.RunPython(generate_uuids_for_profiles, migrations.RunPython.noop),
        
        # Step 3: Add temporary UUID foreign key field
        migrations.AddField(
            model_name='userprofile',
            name='team_uuid',
            field=models.UUIDField(null=True),
        ),
        
        # Step 4: Update foreign key references
        migrations.RunPython(update_team_foreign_keys_forward, update_team_foreign_keys_reverse),
        
        # Step 5: Remove old foreign key
        migrations.RemoveField(
            model_name='userprofile',
            name='team',
        ),
        
        # Step 6: Remove old primary keys
        migrations.RemoveField(
            model_name='team',
            name='id',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='id',
        ),
        
        # Step 7: Rename UUID fields to id and make them primary keys
        migrations.RenameField(
            model_name='team',
            old_name='uuid_id',
            new_name='id',
        ),
        migrations.RenameField(
            model_name='userprofile',
            old_name='uuid_id',
            new_name='id',
        ),
        migrations.RenameField(
            model_name='userprofile',
            old_name='team_uuid',
            new_name='team',
        ),
        
        # Step 8: Make UUID fields primary keys and set up foreign key properly
        migrations.AlterField(
            model_name='team',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
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
    ]

