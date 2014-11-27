#!/usr/bin/env python

from __future__ import absolute_import

import os, sys

from celery import Celery
from celery.schedules import crontab

from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domain_checker.settings.template')

app = Celery('domain_checker')
app.config_from_object('django.conf:settings')
app.conf.update(
    BROKER_URL='amqp://domainpan:dppassw@localhost:5672/domainpan',
    BROKER_HOST='localhost',
    BROKER_USER='domainpan',
    BROKER_PASSWORD = 'dppassw',
    CELERY_RESULT_BACKEND = 'amqp',
    CELERY_FORCE_BILLIARD_LOGGING=False,
    CELERY_IMPORTS=('main.tasks', 'domain_checker'),

    CELERYBEAT_SCHEDULE = {
        'check_tasks' : {
            'task' : 'main.tasks.check_project_tasks',
            'schedule' : crontab(minute='*/5'),
        },
        'moz_api' : {
            'task' : 'main.tasks.update_metrics',
            'schedule' : crontab(minute='*/5'),
        },
        'check_moz_updatetime' : {
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


