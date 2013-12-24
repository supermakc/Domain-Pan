#!/usr/bin/env python

from __future__ import absolute_import

import os, sys

from celery import Celery
from celery.schedules import crontab

from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domain_checker.settings.production')

app = Celery('domain_checker')
app.config_from_object('django.conf:settings')
app.conf.update(
    BROKER_URL='amqp://dc_user:password@localhost//',
    BROKER_HOST='localhost',
    BROKER_USER='dc_user',
    BROKER_PASSWORD = 'password',
    CELERY_RESULT_BACKEND = 'amqp',
    CELERY_FORCE_BILLIARD_LOGGING=False,
    CELERY_IMPORTS=('main.tasks', 'domain_checker'),

    CELERYBEAT_SCHEDULE = {
        'check_tasks' : {
            'task' : 'main.tasks.check_project_tasks',
            'schedule' : crontab(minute='*/5'),
        },
        'moz_api' : {
            'task' : 'main.tasks.update_domain_metrics',
            'schedule' : crontab(minute='0'),
        },
        'moz_api_update' : {
            'task' : 'main.tasks.check_moz_update',
            'schedule' : crontab(hour='0'),
        },
    },
)
# app.autodiscover_tasks(lambda: settings.INSTALLED_APPS, related_name='tasks')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# print sys.path

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


