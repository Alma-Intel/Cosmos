"""
Custom template filters for user-related display
"""
from django import template

register = template.Library()


@register.filter
def display_name(user):
    """
    Returns the user's display name: first_name + last_name if available,
    otherwise username.
    """
    if not user:
        return ""
    
    if user.first_name or user.last_name:
        # Join first and last name, strip extra whitespace
        name_parts = [part for part in [user.first_name, user.last_name] if part]
        return " ".join(name_parts).strip()
    
    return user.username

