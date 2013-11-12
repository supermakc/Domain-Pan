#!/usr/bin/env python

from __future__ import absolute_import

import os

from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domain_checker.settings')

app = Celery('domain_checker', broker='django://')
app.config_from_object('django.conf:settings')
app.conf.update(
    # BROKER_BACKEND='django',
    CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend',
    CELERY_FORCE_BILLIARD_LOGGING=False,
)
app.autodiscover_tasks(settings.INSTALLED_APPS, related_name='tasks')

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

