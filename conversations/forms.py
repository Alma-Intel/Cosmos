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
        required=False,
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
        queryset=Team.objects.none(),  # Will be set in __init__
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
    alma_internal_organization = forms.CharField(
        max_length=255,
        required=False,
        label='ALMA Internal Organization',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter ALMA internal organization'
        }),
        help_text='Only visible to admins'
    )
    new_password = forms.CharField(
        max_length=128,
        required=False,
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Leave blank to keep current password'
        }),
        help_text='Only admins can change passwords. Leave blank to keep current password.'
    )
    
    def __init__(self, *args, **kwargs):
        profile_instance = kwargs.pop('profile_instance', None)
        user_instance = kwargs.pop('instance', None)
        current_profile = kwargs.pop('current_profile', None)
        super().__init__(*args, **kwargs)
        
        # Filter teams by organization (admins can see all)
        if current_profile:
            if current_profile.is_admin():
                self.fields['team'].queryset = Team.objects.all().order_by('name')
            else:
                if current_profile.alma_internal_organization:
                    self.fields['team'].queryset = Team.objects.filter(alma_internal_organization=current_profile.alma_internal_organization).order_by('name')
                else:
                    self.fields['team'].queryset = Team.objects.none()
        else:
            self.fields['team'].queryset = Team.objects.none()
        
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
            self.fields['alma_internal_organization'].initial = profile_instance.alma_internal_organization or ''
        
            # Hide fields based on permissions
            if current_profile:
                # Only admins can see ALMA internal UUID, Organization, and password
                if not current_profile.is_admin():
                    self.fields['alma_internal_uuid'].widget = forms.HiddenInput()
                    self.fields['alma_internal_organization'].widget = forms.HiddenInput()
                    self.fields['new_password'].widget = forms.HiddenInput()
            
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
        required=False,
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
        queryset=Team.objects.none(),  # Will be set in __init__
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
    alma_internal_organization = forms.CharField(
        max_length=255,
        required=False,
        label='ALMA Internal Organization',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter ALMA internal organization'
        }),
        help_text='Only visible to admins'
    )
    
    def __init__(self, *args, **kwargs):
        current_profile = kwargs.pop('current_profile', None)
        super().__init__(*args, **kwargs)
        
        # Filter teams by organization (admins can see all)
        if current_profile:
            if current_profile.is_admin():
                self.fields['team'].queryset = Team.objects.all().order_by('name')
            else:
                if current_profile.alma_internal_organization:
                    self.fields['team'].queryset = Team.objects.filter(alma_internal_organization=current_profile.alma_internal_organization).order_by('name')
                else:
                    self.fields['team'].queryset = Team.objects.none()
        else:
            self.fields['team'].queryset = Team.objects.none()
        
        # Hide fields based on permissions
        if current_profile:
            # Only admins can see ALMA internal UUID and Organization
            if not current_profile.is_admin():
                self.fields['alma_internal_uuid'].widget = forms.HiddenInput()
                self.fields['alma_internal_organization'].widget = forms.HiddenInput()
            
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
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email


class TeamCreateForm(forms.ModelForm):
    """Form for creating new teams - requires a manager to be assigned"""
    manager = forms.ModelChoiceField(
        queryset=UserProfile.objects.none(),  # Will be set in __init__
        required=True,
        label='Manager',
        help_text='Select a Manager, Director, or Admin to assign to this team',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = Team
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter team name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter team description (optional)',
                'rows': 3
            })
        }
        labels = {
            'name': 'Team Name',
            'description': 'Description'
        }
    
    def __init__(self, *args, **kwargs):
        # Pop current_profile before calling super() since ModelForm doesn't accept it
        current_profile = kwargs.pop('current_profile', None)
        super().__init__(*args, **kwargs)
        
        # Set required fields
        self.fields['name'].required = True
        self.fields['description'].required = False
        
        # Filter managers by organization (admins can see all)
        if current_profile:
            if current_profile.is_admin():
                self.fields['manager'].queryset = UserProfile.objects.filter(role__in=['Manager', 'Director', 'Admin']).select_related('user').order_by('user__last_name', 'user__first_name', 'user__username')
            else:
                if current_profile.alma_internal_organization:
                    self.fields['manager'].queryset = UserProfile.objects.filter(
                        role__in=['Manager', 'Director', 'Admin'],
                        alma_internal_organization=current_profile.alma_internal_organization
                    ).select_related('user').order_by('user__last_name', 'user__first_name', 'user__username')
                else:
                    self.fields['manager'].queryset = UserProfile.objects.none()
        else:
            self.fields['manager'].queryset = UserProfile.objects.none()


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
        required=False,
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
    new_password = forms.CharField(
        max_length=128,
        required=False,
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Leave blank to keep current password'
        }),
        help_text='Leave blank to keep your current password.'
    )
    confirm_password = forms.CharField(
        max_length=128,
        required=False,
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        }),
        help_text='Re-enter the new password to confirm.'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password or confirm_password:
            if not new_password:
                raise forms.ValidationError('Please enter a new password.')
            if not confirm_password:
                raise forms.ValidationError('Please confirm your new password.')
            if new_password != confirm_password:
                raise forms.ValidationError('Passwords do not match.')
        
        return cleaned_data
    
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

