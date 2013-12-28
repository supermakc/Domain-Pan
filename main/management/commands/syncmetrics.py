from django.core.management.base import BaseCommand, CommandError
from main.models import UserProject, ProjectDomain, URLMetrics

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
        pdr = 0
        pdra = 0
        pda = 0
        pdaa = 0
        dur = 0
        for pd in ProjectDomain.objects.all():
            ums = URLMetrics.objects.filter(query_url=pd.domain).order_by('-last_updated')
            if len(ums) == 0:
                pdr += 1
                if pd.state == 'available':
                    pdra += 1
                if not options['check_only']:
                    pd.url_metrics = None
            else:
                pda += 1
                if pd.state == 'available':
                    pdaa += 1
                if not options['check_only']:
                    pd.url_metrics = ums[0]
            if not options['check_only']:
                pd.save()
                if len(ums) > 1:
                    for um in ums[1:]:
                        um.delete()
                        dur += 1
        if not options['check_only']:
            for p in UserProject.objects.all():
                p.update_state()
        self.stdout.write('Statistics %s:' % ('' if not options['check_only'] else '(check only)'))
        self.stdout.write('  Linked domain entries: %d' % pda)
        self.stdout.write('      Available: %d' % pdaa)
        self.stdout.write('  Unlinked domain entries: %d' % pdr)
        self.stdout.write('      Available: %d' % pdra)
        self.stdout.write('  Duplicate metric records removed: %d' % dur)
        self.stdout.write('  Total metric records remaining: %d' % (len(URLMetrics.objects.all())))

