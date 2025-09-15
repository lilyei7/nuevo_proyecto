from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from hotels.models import UserProfile


class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form with additional fields"""
    first_name = forms.CharField(max_length=30, required=False, help_text='Nombre')
    last_name = forms.CharField(max_length=30, required=False, help_text='Apellidos')
    email = forms.EmailField(max_length=254, help_text='Email')
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile"""
    first_name = forms.CharField(max_length=30, required=False, label='Nombre')
    last_name = forms.CharField(max_length=30, required=False, label='Apellidos')
    email = forms.EmailField(max_length=254, required=False, label='Email')
    
    class Meta:
        model = UserProfile
        fields = ['role', 'phone', 'avatar', 'dark_mode', 'email_notifications']
        widgets = {
            'avatar': forms.FileInput(attrs={'accept': 'image/*'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-control'})
            else:
                field.widget.attrs.update({'class': 'form-check-input'})
        
        # Make role read-only for non-admin users
        if hasattr(self, 'instance') and self.instance.user and not self.instance.user.is_superuser:
            self.fields['role'].widget.attrs['readonly'] = True
