from django.core.management.base import BaseCommand, CommandError
from main.models import ProjectDomain, URLMetrics

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
                pd.urlmetrics_id = None
            else:
                pda += 1
                pd.urlmetrics_id = ums[0].id
            pd.save()
            if len(ums) > 1:
                for um in ums:
                    um.delete()
                    dur += 1
        print 'Statistics:'
        print '  Linked domain entries: %d' % pda
        print '  Unlinked domain entries: %d' % pdr
        print '  Duplicate metric records removed: %d' % dur
        print '  Total metric records remaining: %d' % (len(URLMetrics.objects.all()))

