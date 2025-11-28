from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'external_uuid', 'cell_phone', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'external_uuid', 'cell_phone')
    readonly_fields = ('created_at', 'updated_at')
# Note: Since we're using MongoDB directly, we don't have Django models to register.
# This file is kept for future use if you want to add Django models for other features.

