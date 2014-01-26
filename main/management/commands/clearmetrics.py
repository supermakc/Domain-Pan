"""
Deletes all URLMetrics in the database (intended for testing purposes only).
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from main.models import UserProject, ProjectDomain, URLMetrics, ProjectMetrics

from optparse import make_option

class Command(BaseCommand):
    help = 'Deletes all metrics in the database'

    def handle(self, *args, **options):
        count = 0
        for um in URLMetrics.objects.all():
            count += 1
            ProjectMetrics.objects.filter(urlmetrics=um).delete()
            um.delete()
            
        self.stdout.write(u'Total metric removed: %d' % count)
