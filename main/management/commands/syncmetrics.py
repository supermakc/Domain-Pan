"""
Restores any missing project domain/metrics associations.  If any duplicates are found, they are deleted.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
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
        pm_total = 0
        pm_checked = 0
        dup_removed = 0
        with transaction.atomic():
            for p in UserProject.objects.all():
                for pm in ProjectMetrics.objects.filter(project=p, is_extension=False):
                    pm.delete()

                for pm in ProjectMetrics.objects.filter(project=p, is_extension=True):
                    if pm.urlmetrics.is_uptodate():
                        pm_checked += 1
                        pm.is_checked = True
                    else:
                        pm.is_checked = False

                for pd in p.projectdomain_set.filter(state=u'available'):
                    ums = URLMetrics.objects.filter(query_url=pd.domain).order_by(u'-last_updated')
                    if len(ums) == 0:
                        um = URLMetrics(query_url=pd.domain)
                        um.save()
                        pm = ProjectMetrics(project=p, urlmetrics=um, is_checked=False)
                        pm.save()
                    else:
                        if len(ums) > 1:
                            for dum in ums[1:]:
                                dup_removed += 1
                                dum.delete()
                        um = ums[0]
                        pm = ProjectMetrics(project=p, urlmetrics=um)
                        if um.is_uptodate():
                            pm.is_checked = True
                            pm_checked += 1
                        else:
                            pm.is_checked = False
                        pm.save()
                    pm_total += 1
        self.stdout.write('Statistics:')
        self.stdout.write('  Project metric links: %d' % pm_total)
        self.stdout.write('      Checked/up-to-date: %d' % pm_checked)
        self.stdout.write('  Duplicate metric records removed: %d' % dup_removed)
        self.stdout.write('  Total metric records (post-removal): %d' % (len(URLMetrics.objects.all())))

