from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

# Definimos una clase de estilo común para los campos
INPUT_CLASSES = 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'

class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        label="Nombre de usuario",
        widget=forms.TextInput(attrs={'class': INPUT_CLASSES})
    )
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={'class': INPUT_CLASSES})
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': INPUT_CLASSES})
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={'class': INPUT_CLASSES})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este email ya está registrado. Por favor utilice otro.")
        return email


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuario o Email",
        widget=forms.TextInput(attrs={'class': INPUT_CLASSES})
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': INPUT_CLASSES})
    )
    
    error_messages = {
        'invalid_login': "Por favor ingrese un usuario/email y contraseña correctos. "
                        "Los datos ingresados no coinciden con nuestros registros.",
        'inactive': "Esta cuenta está inactiva."
    }