from defaults import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dbname',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': 'dbuser',
        'PASSWORD': 'password',
        'HOST': 'dbhost',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Admin One', 'admin1@domain.com'),
    ('Admin Two', 'admin2@domain.com'),
)

MANAGERS = ADMINS

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['domain.com']

MEDIA_ROOT='/path/to/domain_checker/media'

