"""
Django settings for janaypedidos project.
"""

from pathlib import Path
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
import os
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# En producción usa variable de entorno, en desarrollo usa env.py
if os.environ.get('SECRET_KEY'):
    SECRET_KEY = os.environ.get('SECRET_KEY')
else:
    try:
        from .env import secret_key
        SECRET_KEY = secret_key()
    except ImportError:
        # Fallback para desarrollo si no existe env.py
        SECRET_KEY = 'django-insecure-dev-key-change-this-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [
    'localhost', '127.0.0.1',
    'janaypedidos-55029af11574.herokuapp.com',
    'janaypedidos.herokuapp.com',
    'janaypedidos.page', 'www.janaypedidos.page',
]
CSRF_TRUSTED_ORIGINS = [
    'https://janaypedidos.page',
    'https://www.janaypedidos.page',
    'https://janaypedidos-55029af11574.herokuapp.com',
    'https://janaypedidos.herokuapp.com',
]

# Application definition

INSTALLED_APPS = [
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'tailwind',
    'theme',
    'django_browser_reload',
    'accounts',
    'products',
    'orders',
    'history',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

ROOT_URLCONF = 'janaypedidos.urls'

TAILWIND_APP_NAME = 'theme'

# NPM path - diferente para desarrollo y producción
if os.environ.get('DYNO'):  # Heroku environment
    NPM_BIN_PATH = '/usr/bin/npm'
else:
    NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"

INTERNAL_IPS = [
    "127.0.0.1",
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'janaypedidos.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# Configuración de base de datos con PostgreSQL para producción
if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'es-es'

TIME_ZONE = 'America/Bogota'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

# Configuración completa de archivos estáticos
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise configuration
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuración de autenticación
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Configuración para archivos multimedia
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_BUCKET = os.environ.get('SUPABASE_BUCKET', 'products')

SUPABASE_STORAGE = {
    "url": SUPABASE_URL,
    "service_role_key": SUPABASE_SERVICE_ROLE_KEY,
    "bucket": SUPABASE_BUCKET,
    "base_path": "products",
}

if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    DEFAULT_FILE_STORAGE = "products.supabase_storage.SupabaseStorage"

# Security settings para producción
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Excluir localhost del redirect SSL
    SECURE_REDIRECT_EXEMPT = [r'^(?!admin).*$'] if os.environ.get('DYNO') is None else []
else:
    # Asegurar que en DEBUG no se aplique nada de SSL
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0

# Configuración de Unfold
UNFOLD = {
    # Branding y apariencia
    "SITE_TITLE": "Janay Pedidos",
    "SITE_HEADER": "Administración Janay",
    "SITE_SUBHEADER": "Panel de Control",
    "SITE_SYMBOL": "dashboard",
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/svg+xml",
            "href": lambda request: static("images/coffee_light.svg"),
        },
    ],
    "LOGIN": {
        "image": lambda request: static("images/coffee_beans.jpg"),
    },

    # Colores - Paleta Naranja
    "COLORS": {
        "primary": {
            "50": "255 247 237",  # Naranja muy claro
            "100": "255 237 213", 
            "200": "254 215 170",
            "300": "253 186 116", 
            "400": "251 146 60",  
            "500": "249 115 22",  # Naranja principal - coincide con tu frontend
            "600": "234 88 12",   
            "700": "194 65 12",   
            "800": "154 52 18",   
            "900": "124 45 18",   
            "950": "67 20 7",     
        },
        # Colores base - De blanco a negro
        "base": {
            "50": "220 220 230",   # color general navbar y cuadros
            "100": "253 186 116",  # Blanco grisáceo caja de seleccion del navbar
            "200": "10 10 10",  # Gris claro lineas de separacion
            "300": "200 200 200",  # negro claro blackmode color letras en light color cuadrados
            "400": "253 186 116",  # naranja principal - bien 100%
            "500": "234 88 12",  # GRIS MEDIO (mitad)
            "600": "50 50 50",     # Gris oscuro
            "700": "150 150 150",     # Gris muy oscuro
            "800": "100 100 100",     # Negro grisáceo
            "900": "65 65 65",     # color principal en black mode
            "950": "150 150 150",        # NEGRO PURO (final)
        }
        },
        
    # Personalización de la barra lateral
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Users & groups"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "account_circle",
                        "link": reverse_lazy("admin:auth_user_changelist")
                    },
                    {
                        "title": _("Groups"),
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist")
                    },
                ]
            },
            {
                "title": _("Products"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Categories"),
                        "icon": "category",
                        "link": reverse_lazy("admin:products_category_changelist")
                        
                    },
                    {
                        "title": _("Products"),
                        "icon": "inventory",
                        "link": reverse_lazy("admin:products_product_changelist")
                    },
                ]
            },
            {
                "title": _("Orders"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Orders"),
                        "icon": "shopping_cart",
                        "link": reverse_lazy("admin:orders_order_changelist")
                    },
                    {
                        "title": _("Order Items"),
                        "icon": "list_alt",
                        "link": reverse_lazy("admin:orders_orderitem_changelist")
                    },
                    {
                        "title": _("Modification Requests"),
                        "icon": "edit_note",
                        "link": reverse_lazy("admin:orders_ordermodificationrequest_changelist")
                    },
                    {
                        "title": _("Business Settings"),
                        "icon": "settings",
                        "link": reverse_lazy("admin:orders_businesssettings_changelist")
                    },
                ]
            }
        ]
    },
    
    # Personalización de UI
    "ENVIRONMENT": [
        os.environ.get("UNFOLD_ENVIRONMENT", "DESARROLLO"),
        "primary",
    ],
    "BORDER_RADIUS": "6px",
    "DARK_MODE": True,  # Activar modo oscuro
    
    # Personalización de textos
    "CUSTOM_TEXTS": {
        "action_submit": "Guardar cambios",
        "action_add_another": "Guardar y añadir otro",
        "action_continue": "Guardar y continuar editando",
    },
}
