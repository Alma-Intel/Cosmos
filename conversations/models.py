"""
Models for the conversations app
"""
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """Extended user profile information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    external_uuid = models.CharField(max_length=255, blank=True, null=True, verbose_name='External UUID')
    cell_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Cell Phone')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'userprofile'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

