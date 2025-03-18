from django.shortcuts import render
from django.contrib.auth.views import LoginView
from django.views.generic import CreateView
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm, CustomAuthenticationForm

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    form_class = CustomAuthenticationForm

class CustomSignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('login')

# Create your views here.
