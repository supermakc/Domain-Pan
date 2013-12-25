from django.core.management.base import BaseCommand, CommandError
from main.models import AdminSetting, TLD, ExcludedDomain

class Command(BaseCommand):
    help = 'Imports default static data (TLD\'s, excluded domains, administration settings) into database for new installations.'

    def handle(self, *args, **options):
        tld_filename = 'tld_list.txt'
        exclusion_filename = 'exclusion_domains.txt'
        settings_filename = 'clean_admin.txt'

        tldf = open(tld_filename)
        tlds = [line.strip() for line in tldf if line[0] not in '/\n']
        tldf.close()
        exf = open(exclusion_filename)
        exl = [line.strip() for line in exf]
        exf.close()
        sf = open(settings_filename)
        ss = [line.strip() for line in sf]
        sf.close()

        tic = 0
        for tld in tlds:
            try:
                t = TLD.objects.get(domain=tld)
            except TLD.DoesNotExist:
                t = TLD()
                t.domain = tld
                t.is_recognized = False
                t.is_api_registerable = False
                t.description = None
                t.type = ''
                t.save()
                tic += 1
        self.stdout.write('TLDs: Inserted %d row(s) (out of %d TLDs)' % (tic, len(tlds)))

        eic = 0
        for exd in exl:
            try:
                ed = ExcludedDomain.objects.get(domain=exd)
            except ExcludedDomain.DoesNotExit:
                ed = ExcludedDomain()
                ed.domain = exd
                exd.save()
                eic += 1
        self.stdout.write('Excluded domains: Inserted %d row(s) (out of %d listed domains)' % (eic, len(exl)))

        sic = 0
        for s in ss:
            if len(s) == 0:
                continue
            vals = s.split('\t')
            key = vals[0]
            value = vals[1]
            valtype = vals[2]
            choices = None
            if len(vals) > 3:
                choices = vals[4]
            try:
                aso = AdminSetting.objects.get(key=key)
            except AdminSetting.DoesNotExist:
                aso = AdminSetting()
                aso.key = key
                aso.value = value
                aso.type = valtype
                aso.choices = choices
                aso.save()
                sic += 1
        self.stdout.write('Admin settings: Inserted %d row(s) (out of %d listed settings)' % (sic, len(ss)))

