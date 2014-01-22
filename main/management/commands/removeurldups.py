from django.core.management.base import BaseCommand, CommandError
from main.models import UserProject, ProjectDomain, URLMetrics, ProjectMetrics

from optparse import make_option

class Command(BaseCommand):
    help = 'Syncronises foreign keys between project domains and URL metrics records.'
    option_list = BaseCommand.option_list + (
        make_option('--check_only',
            action='store_true',
            dest='check_only',
            default=False,
            help='Report on currently syncronised metrics only'),
        )

    def handle(self, *args, **options):
        dup_urls = 0
        dups_removed = 0
        found_dup = True
        while found_dup:
            found_dup = False
            for um in URLMetrics.objects.all():
                dups = URLMetrics.objects.filter(query_url=um.query_url).exclude(id=um.id)
                if dups.count() > 0:
                    self.stdout.write(u'  %s' % um.query_url)
                    dup_urls += 1
                    for dup in dups:
                        dups_removed += 1
                        for pm in ProjectMetrics.objects.filter(urlmetrics=dup):
                            pm.delete()
                        dup.delete()
                    found_dup = True
                    break
        self.stdout.write('Results:')
        self.stdout.write('  Records with duplicates: %d' % dup_urls)
        self.stdout.write('  Total records removed: %d' % dups_removed)
