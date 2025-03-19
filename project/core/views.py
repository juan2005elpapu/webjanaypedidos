from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect


class HomeView(LoginRequiredMixin, TemplateView):
    """Vista del dashboard principal tras iniciar sesión"""
    template_name = 'core/home.html'
    login_url = 'login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Dashboard - Janay Pedidos'
        return context


class WelcomeView(TemplateView):
    """Página de bienvenida pública"""
    template_name = 'welcome.html'  # Cambiado para usar el template en la carpeta raíz
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:home')
        return super().dispatch(request, *args, **kwargs)
