from django.core.management.base import BaseCommand, CommandError
from main.models import UserProject, ProjectDomain, URLMetrics

class Command(BaseCommand):
    help = 'Syncronises foreign keys between project domains and URL metrics records.'

    def handle(self, *args, **options):
        pdr = 0
        pda = 0
        dur = 0
        for pd in ProjectDomain.objects.all():
            ums = URLMetrics.objects.filter(query_url=pd.domain).order_by('-last_updated')
            if len(ums) == 0:
                pdr = 0
                pd.url_metrics = None
            else:
                pda += 1
                pd.url_metrics = ums[0]
            pd.save()
            if len(ums) > 1:
                for um in ums[1:]:
                    um.delete()
                    dur += 1
        for p in UserProject.objects.all():
            p.update_state()
        self.stdout.write('Statistics:')
        self.stdout.write('  Linked domain entries: %d' % pda)
        self.stdout.write('  Unlinked domain entries: %d' % pdr)
        self.stdout.write('  Duplicate metric records removed: %d' % dur)
        self.stdout.write('  Total metric records remaining: %d' % (len(URLMetrics.objects.all())))

