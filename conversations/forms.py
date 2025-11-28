"""
Forms for the conversations app
"""
from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, Team


class AgentEditForm(forms.Form):
    """Form for editing agent profiles with role-based permissions"""
    first_name = forms.CharField(
        max_length=150,
        required=False,
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )
    email = forms.EmailField(
        required=True,
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        required=True,
        label='Role',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    team = forms.ModelChoiceField(
        queryset=Team.objects.all(),
        required=False,
        label='Team',
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        empty_label='No Team'
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
    alma_internal_uuid = forms.CharField(
        max_length=255,
        required=False,
        label='ALMA Internal UUID',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter ALMA internal UUID'
        }),
        help_text='Only visible to admins'
    )
    
    def __init__(self, *args, **kwargs):
        profile_instance = kwargs.pop('profile_instance', None)
        user_instance = kwargs.pop('instance', None)
        current_profile = kwargs.pop('current_profile', None)
        super().__init__(*args, **kwargs)
        
        if user_instance:
            self.fields['first_name'].initial = user_instance.first_name
            self.fields['last_name'].initial = user_instance.last_name
            self.fields['email'].initial = user_instance.email
        
        if profile_instance:
            self.fields['role'].initial = profile_instance.role
            self.fields['team'].initial = profile_instance.team
            self.fields['external_uuid'].initial = profile_instance.external_uuid or ''
            self.fields['cell_phone'].initial = profile_instance.cell_phone or ''
            self.fields['alma_internal_uuid'].initial = profile_instance.alma_internal_uuid or ''
        
            # Hide fields based on permissions
            if current_profile:
                # Only admins can see ALMA internal UUID
                if not current_profile.is_admin():
                    self.fields['alma_internal_uuid'].widget = forms.HiddenInput()
            
            # Note: Role and team permission checks are handled in the view
            # We show the fields but validate permissions when saving


class UserCreateForm(forms.Form):
    """Form for creating new users"""
    username = forms.CharField(
        max_length=150,
        required=True,
        label='Username',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username'
        }),
        help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )
    email = forms.EmailField(
        required=True,
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )
    password = forms.CharField(
        required=True,
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        }),
        help_text='Password for the new user account'
    )
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        required=True,
        label='Role',
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        initial='User'
    )
    team = forms.ModelChoiceField(
        queryset=Team.objects.all(),
        required=False,
        label='Team',
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        empty_label='No Team'
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
    alma_internal_uuid = forms.CharField(
        max_length=255,
        required=False,
        label='ALMA Internal UUID',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter ALMA internal UUID'
        }),
        help_text='Only visible to admins'
    )
    
    def __init__(self, *args, **kwargs):
        current_profile = kwargs.pop('current_profile', None)
        super().__init__(*args, **kwargs)
        
        # Hide fields based on permissions
        if current_profile:
            # Only admins can see ALMA internal UUID
            if not current_profile.is_admin():
                self.fields['alma_internal_uuid'].widget = forms.HiddenInput()
            
            # Directors can only create Users and Managers
            if current_profile.is_director() and not current_profile.is_admin():
                self.fields['role'].choices = [
                    choice for choice in UserProfile.ROLE_CHOICES 
                    if choice[0] in ['User', 'Manager']
                ]
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email


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

