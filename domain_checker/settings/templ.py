'''

!!!Please, rename this file to template.py!!!

'''

from defaults import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dbname',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': 'user',
        'PASSWORD': 'passwd',
        'HOST': 'localhost',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Admin One', 'admin1@domain.com'),
    ('Admin Two', 'admin2@domain.com'),
)

MANAGERS = ADMINS

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

MEDIA_ROOT='/change_this_url/'

