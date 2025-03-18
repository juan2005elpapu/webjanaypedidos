from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        
        # Primero intenta con username exacto (que debe ser único)
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            pass
            
        # Si no encuentra, intenta con email pero usando filter().first() para evitar MultipleObjectsReturned
        try:
            user = User.objects.filter(email=username).first()
            if user and user.check_password(password):
                return user
        except:
            pass
            
        return None