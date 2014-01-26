"""
Prints out metrics statistics on all projects in the database.
"""
from django.core.management.base import BaseCommand, CommandError
from main.models import UserProject, ProjectDomain, URLMetrics

class Command(BaseCommand):
    help = 'Prints out project statistical information'

    def handle(self, *args, **options):
        for p in UserProject.objects.all():
            self.stdout.write('Filename: %s' % p.name())
            self.stdout.write('  User: %s' % p.user.username)
            self.stdout.write('  Measurable domains:')
            for pd in p.measurable_domains():
                self.stdout.write('    %s' % pd.domain)
            self.stdout.write('  Measured domains:')
            for pd in p.get_measured_domains():
                self.stdout.write('    %s' % pd.domain)

