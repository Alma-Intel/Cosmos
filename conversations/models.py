"""
Models for the conversations app
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Team(models.Model):
    """Team model - each team must have a Manager or Director"""
    name = models.CharField(max_length=255, unique=True, verbose_name='Team Name')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    alma_internal_organization = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='ALMA Internal Organization',
        help_text='Internal Organization - only visible to admins'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Validate that team has at least one Manager or Director"""
        super().clean()
        # This validation will be checked when saving team members
        # We can't validate here because team members are saved separately
    
    def has_manager_or_director(self):
        """Check if team has at least one Manager or Director"""
        return self.userprofile_set.filter(role__in=['Manager', 'Director']).exists()


class UserProfile(models.Model):
    """Extended user profile information"""
    ROLE_CHOICES = [
        ('User', 'User'),
        ('Manager', 'Manager'),
        ('Director', 'Director'),
        ('Admin', 'Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='User',
        verbose_name='Role'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        verbose_name='Team'
    )
    external_uuid = models.CharField(max_length=255, blank=True, null=True, verbose_name='External UUID')
    alma_internal_uuid = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='ALMA Internal UUID',
        help_text='Internal UUID - only visible to admins'
    )
    alma_internal_organization = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='ALMA Internal Organization',
        help_text='Internal Organization - only visible to admins'
    )
    cell_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Cell Phone')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['user__last_name', 'user__first_name', 'user__username']
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def clean(self):
        """Validate team has Manager or Director when assigning team"""
        super().clean()
        if self.team:
            # Check if team will have a Manager or Director after this save
            # (excluding current user if updating)
            other_managers = self.team.members.exclude(
                pk=self.pk if self.pk else None
            ).filter(role__in=['Manager', 'Director', 'Admin'])
            
            # If this user is not a Manager/Director/Admin and there are no others, raise error
            if self.role not in ['Manager', 'Director', 'Admin'] and not other_managers.exists():
                raise ValidationError({
                    'team': 'Team must have at least one Manager, Director, or Admin. Either assign a Manager/Director/Admin to this team or change this user\'s role to Manager, Director, or Admin.'
                })
    
    def get_display_name(self):
        """Get display name: first + last name or username"""
        if self.user.first_name or self.user.last_name:
            name_parts = [part for part in [self.user.first_name, self.user.last_name] if part]
            return " ".join(name_parts).strip()
        return self.user.username
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'Admin'
    
    def is_director(self):
        """Check if user is director"""
        return self.role == 'Director'
    
    def is_manager(self):
        """Check if user is manager"""
        return self.role == 'Manager'
    
    def can_manage_user(self, target_user_profile):
        """Check if this user can manage the target user"""
        if self.is_admin():
            return True
        if self.is_director():
            # Directors can manage anyone
            return True
        if self.is_manager():
            # Managers can only manage users in their team
            return (target_user_profile.team == self.team and 
                    target_user_profile.role in ['User', 'Manager'])
        return False
    
    def can_change_role(self, target_user_profile):
        """Check if this user can change the role of target user"""
        if self.is_admin():
            return True
        if self.is_director():
            # Directors can change users between User and Manager
            return target_user_profile.role in ['User', 'Manager']
        return False

