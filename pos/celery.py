# myproject/celery.py
from __future__ import absolute_import, unicode_literals
import os
import sys

from celery import Celery

if not getattr(sys, 'frozen', False):
    from celery import Celery

    app = Celery('pos')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()

else:
    # Set the default Django settings module for the 'celery' program.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos.settings')

    app = Celery('pos')

    # Using a string here means the worker does not have to serialize
    # the configuration object to child processes.
    app.config_from_object('django.conf:settings', namespace='CELERY')

    # Load task modules from all registered Django app configs.
    app.autodiscover_tasks()
