Domain-Checker
==============

Essential libraries that must be installed:

* Django 1.6 (remove old first)

* libffi-dev
* bcrypt (must run django createsuperuser first time as root; bcrypt seems to want to compile things to the dist-package __pycache__ directory first)
* libmysqlclient-dev
* mysql-python

* celery-3.1.6
* billiard (should be installed automatically with Celery)
* django-celery-3.1.1

* lockfile-0.9.1
* lxml-3.2.4

* rabbitmq-server (3.2.1 or latest, note this is a non-Python library)
* librabbitmq-1.0.3

Installation Tasks
------------------

1. Set up Apache 2 with mod_wsgi.  Have mod_wsgi point to the appropriate wsgi_* file in domain_checker/ directory.
2. Set up celeryd and celerybeat.  CELERY_CHDIR must be set to the installation directory and CELERY_APP must be set to 'domain_checker'.
3. Set up the cronjob for restarting celery if required.  The appropriate executable and script can be found in the 'celerymon' directory.
4. Perform django syncdb, create at least one django superuser, restart Apache, celeryd and celerybeat
5. Test to satisfaction.
