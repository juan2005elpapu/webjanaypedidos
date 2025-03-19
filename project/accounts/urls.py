from django.urls import path
from django.views.generic import RedirectView
from .views import CustomLoginView, CustomSignUpView
from django.contrib.auth.views import LogoutView


urlpatterns = [
    # Redirecciona la URL 'accounts/' a 'accounts/login/'
    path('', RedirectView.as_view(pattern_name='login'), name='accounts_root'),
    
    # Rutas existentes
    path('login/', CustomLoginView.as_view(), name='login'),
    path('signup/', CustomSignUpView.as_view(), name='signup'),
    # Cambiamos next_page a 'core:welcome' en lugar de 'login'
    path('logout/', LogoutView.as_view(next_page='welcome'), name='logout'),
]