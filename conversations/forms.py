"""
Forms for the conversations app
"""
from django import forms
from django.contrib.auth.models import User
from .models import UserProfile


class ProfileForm(forms.Form):
    """Form for editing user profile"""
    first_name = forms.CharField(
        max_length=150,
        required=False,
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )
    email = forms.EmailField(
        required=True,
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    external_uuid = forms.CharField(
        max_length=255,
        required=False,
        label='External UUID',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter external UUID'
        })
    )
    cell_phone = forms.CharField(
        max_length=20,
        required=False,
        label='Cell Phone',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter cell phone number'
        })
    )
    
    def __init__(self, *args, **kwargs):
        profile_instance = kwargs.pop('profile_instance', None)
        user_instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
        
        if user_instance:
            self.fields['first_name'].initial = user_instance.first_name
            self.fields['last_name'].initial = user_instance.last_name
            self.fields['email'].initial = user_instance.email
        
        if profile_instance:
            self.fields['external_uuid'].initial = profile_instance.external_uuid or ''
            self.fields['cell_phone'].initial = profile_instance.cell_phone or ''

