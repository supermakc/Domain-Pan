from django.core.management.base import BaseCommand, CommandError
from main.models import UserProject, ProjectDomain, URLMetrics

class Command(BaseCommand):
    help = 'Deletes all URL metrics in the system, dissociates project domains, and updates project statuses.'

    def handle(self, *args, **options):
        umc = 0
        for um in URLMetrics.objects.all():
            """
            for pd in ProjectDomain.objects.filter(url_metrics_id=um.id):
                pd.url_metrics = None
                pd.save()
            """
            um.delete()
            umc += 1
        for p in UserProject.objects.all():
            p.update_state()
        self.stdout.write('Total metric records erased: %d' % umc)

