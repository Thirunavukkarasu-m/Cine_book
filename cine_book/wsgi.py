"""WSGI config for the CineBook project."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cine_book.settings')

application = get_wsgi_application()
