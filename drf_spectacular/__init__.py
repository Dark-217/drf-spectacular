import django

__version__ = '0.27.0'

if django.VERSION < (3, 2):
    default_app_config = 'drf_spectacular.apps.SpectacularConfig'
