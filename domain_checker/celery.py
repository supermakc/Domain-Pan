#!/usr/bin/env python

from __future__ import absolute_import

import os, sys

from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domain_checker.settings')

app = Celery('domain_checker', broker='django://')
app.config_from_object('django.conf:settings')
app.conf.update(
    BROKER_BACKEND='django',
    BROKER_HOST='localhost',
    BROKER_USER='dc_user',
    BROKER_PASSWORD = 'password',
    CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend',
    CELERY_FORCE_BILLIARD_LOGGING=False,
    CELERY_IMPORTS=('main.tasks', 'domain_checker'),
)
# app.autodiscover_tasks(lambda: settings.INSTALLED_APPS, related_name='tasks')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# print sys.path

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


