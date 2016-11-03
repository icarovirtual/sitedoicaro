# -*- coding: utf-8 -*-


import os
import sys


activate_this = '/home/ubuntu/sites/sitedoicaro.not.br/env/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

current_path = os.path.dirname(os.path.realpath(__file__))

if current_path not in sys.path:
    sys.path.insert(0, current_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitedoicaro.settings')

from django.core.wsgi import get_wsgi_application


application = get_wsgi_application()
