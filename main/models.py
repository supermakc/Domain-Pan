from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models, transaction
from django.utils import timezone

import hmac, hashlib, base64, time, datetime

MAX_DOMAIN_LENGTH = 255

# MozAPI url-metric result for a single URL
class URLMetrics(models.Model):
    query_url = models.CharField(max_length=MAX_DOMAIN_LENGTH)
    last_updated = models.DateTimeField(null=True, blank=True, default=None)
    extended_from = models.ForeignKey('self', null=True, blank=True, default=None)

    title = models.TextField(null=True, blank=True)
    canonical_url = models.TextField(null=True, blank=True)

    subdomain = models.CharField(max_length=MAX_DOMAIN_LENGTH, null=True, blank=True)
    root_domain = models.CharField(max_length=MAX_DOMAIN_LENGTH, null=True, blank=True)
    external_links = models.FloatField(null=True, blank=True)

    subdomain_external_links = models.IntegerField(null=True, blank=True)
    root_domain_external_links = models.IntegerField(null=True, blank=True)
    equity_links = models.FloatField(null=True, blank=True)

    subdomains_linking = models.IntegerField(null=True, blank=True)
    root_domains_linking = models.IntegerField(null=True, blank=True)
    links = models.FloatField(null=True, blank=True)
    subdomain_subdomains_linking = models.IntegerField(null=True, blank=True)
    root_domain_root_domains_linking = models.IntegerField(null=True, blank=True)
    mozrank_10 = models.FloatField(null=True, blank=True)
    mozrank_raw = models.FloatField(null=True, blank=True)
    subdomain_mozrank_10 = models.FloatField(null=True, blank=True)
    subdomain_mozrank_raw = models.FloatField(null=True, blank=True)
    root_domain_mozrank_10 = models.FloatField(null=True, blank=True)
    root_domain_mozrank_raw = models.FloatField(null=True, blank=True)
    http_status_code = models.IntegerField(null=True, blank=True)
    page_authority = models.FloatField(null=True, blank=True)
    domain_authority = models.FloatField(null=True, blank=True)

    flag_map = {
        'Title' : ['ut', 1],
        'Canonical URL' : ['uu', 4],
        'Subdomain' : ['ufq', 8],
        'Root Domain' : ['upl', 16],
        'External Links' : ['ueid', 32],
        'Subdomain External Links' : ['feid', 64],
        'Root Domain External Links' : ['peid', 128],
        'Equity Links' : ['ujid', 256],
        'Subdomain Linking' : ['uifq', 512],
        'Root Domains Linking' : ['uipl', 1024],
        'Links' : ['uid', 2048],
        'Subdomain Subdomains Linking' : ['fid', 4096],
        'Root Domain Root Domains Linking' : ['pid', 8192],
        'MozRank 10' : ['umrp', 16384],
        'MozRank Raw' : ['umrr', 16384],
        'Subdomain MozRank 10' : ['fmrp', 32768],
        'Subdomain MozRank Raw' : ['fmrr', 32768],
        'Root Domain MozRank 10' : ['pmrp', 65536],
        'Root Domain MozRank Raw' : ['pmrr', 65536],
        'HTTP Status Code' : ['us', 536870912],
        'Page Authority' : ['upa', 34359738368],
        'Domain Authority' : ['pda', 68719476736],
    }

    def store_result(self, rd):
        for k,v in rd.items():
            for fk, fv in URLMetrics.flag_map.items():
                if fv[0] == k:
                    # print k, v, fk, fv
                    attr = fk.lower().replace(' ', '_')
                    # print attr
                    # val = 0 if val '0' else val
                    setattr(self, attr, v)
                    break

    def is_uptodate(self):
        if self.last_updated is None:
            return False
        last_moz_update = MozLastUpdate.get_most_recent()
        return last_moz_update < self.last_updated

    @classmethod
    def create_cols_bitflag(cls, cols):
        bf = 0
        for col in cols:
            bf |= cls.flag_map.get(col, ['', 0])[1]
        return bf


# Top-level domains
class TLD(models.Model):
    domain = models.CharField(max_length=50)
    is_recognized = models.BooleanField(default=False)
    is_api_registerable = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True, null=True, default=None)
    type = models.CharField(max_length=50)

# Domains which should be automatically excluded (e.g. common domains like facebook.com, google.com)
class ExcludedDomain(models.Model):
    domain = models.CharField(max_length=MAX_DOMAIN_LENGTH)

# Domains for which subdomains are preserved
class PreservedDomain(models.Model):
    domain = models.CharField(max_length=MAX_DOMAIN_LENGTH)

# User projects
class UserProject(models.Model):
    PROJECT_STATES = (
        (u'parsing', u'Parsing domains'),
        (u'checking', u'Checking domains'),
        (u'measuring', u'Checking URL metrics'),
        (u'paused', u'Paused'),
        (u'completed', u'Completed'),
        (u'error', u'Error'))
    user = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=20, choices=PROJECT_STATES)
    error = models.TextField(blank=True, null=True, default=None)
    parse_errors = models.TextField(blank=True, null=True, default=None)
    creation_datetime = models.DateTimeField(blank=True, auto_now_add=True)
    completed_datetime = models.DateTimeField(blank=True, null=True)
    completion_email_sent = models.BooleanField(default=False)
    last_updated = models.DateTimeField(null=True, blank=True, default=None)
    urlmetrics = models.ManyToManyField(URLMetrics, through='ProjectMetrics')

    def name(self):
        return self.uploadedfile_set.all()[0].filename

    def send_completion_email(self):
        reply_address = AdminSetting.get_value(u'noreply_address')
        server_address = AdminSetting.get_value(u'server_address')
        messagebody = (u'The project "%s" has successfully completed.  You can view the results at the following address:\n\n' + \
                      u'%s/project?id=%d\n\n' + \
                      u'Thank you for using Domain Checker.') % (self.name(), server_address, self.id)
        send_mail(u'Domain Checker - Project "%s" complete' % (self.name()), messagebody, reply_address, [self.user.email])

    def get_measurable_domains(self):
        return self.urlmetrics.all()

    def get_measured_domains(self):
        return URLMetrics.objects.filter(projectmetrics__project=self, projectmetrics__is_checked=True)
        # return [pm.urlmetrics for pm in ProjectMetrics.objects.filter(project=self,is_checked=True)]

    def get_percent_complete(self):
        checkable_domains = len(self.projectdomain_set.all())
        checked_domains = len(self.projectdomain_set.filter(is_checked=True))

        measurable_domains = len(self.get_measurable_domains())
        measured_domains = len(self.get_measured_domains())

        completed_domains = checked_domains + measured_domains
        total_domains = checkable_domains + measurable_domains

        return 100.0 if total_domains == 0 else (completed_domains*100.0) / total_domains

    def get_percent_complete_display(self):
        return '%.2f' % self.get_percent_complete

    def is_running(self):
        return self.state not in ['completed', 'paused', 'error']

    def all_checked(self):
        return len(self.projectdomain_set.filter(is_checked=False)) == 0

    def all_measured(self):
        return len(self.projectmetrics_set.filter(is_checked=False)) == 0

    def update_state(self, save=True):
        with transaction.atomic():
            if self.state not in ['paused', 'error', 'parsing']:
                if not self.all_checked():
                    new_state = 'checking'
                elif not self.all_measured():
                    new_state = 'measuring'
                else:
                    new_state = 'completed'

                if self.state != new_state:
                    self.updated = timezone.now()
                    if new_state == u'completed':
                        self.send_completion_email()
                        self.completion_email_sent = True
                        self.completed_datetime = timezone.now()
                self.state = new_state
                if save:
                    self.save()

    def run_time(self):
        if not self.is_running():
            if self.completed_datetime is None:
                return 'error'
            return str(self.completed_datetime - self.creation_datetime)
        else:
            return str(timezone.now() - self.creation_datetime)

# Join table relating projects to URL metrics
class ProjectMetrics(models.Model):
    project = models.ForeignKey(UserProject)
    urlmetrics = models.ForeignKey(URLMetrics)
    is_checked = models.BooleanField(default=False)
    is_extension = models.BooleanField(default=False)
    
# Uploaded project files
class UploadedFile(models.Model):
    project = models.ForeignKey(UserProject)
    filename = models.CharField(max_length=255)
    filedata = models.TextField()

# Unique domains calculated for user projects
class ProjectDomain(models.Model):
    DOMAIN_STATES = (
        ('unchecked', 'Unchecked'),
        ('unregisterable', 'Unregisterable'),
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
        ('special', 'Special/Preserved'),
        ('error', 'Error'))
    project = models.ForeignKey(UserProject)
    domain = models.CharField(max_length=MAX_DOMAIN_LENGTH)
    original_link = models.TextField()
    subdomains_preserved = models.BooleanField()
    is_checked = models.BooleanField()
    state = models.CharField(max_length=20, choices=DOMAIN_STATES)
    error = models.TextField(blank=True, null=True, default=None)
    last_checked = models.DateTimeField()
    # url_metrics = models.ForeignKey(URLMetrics, null=True, blank=True, default=None)

# Association between projects and background(Celery) tasks
class ProjectTask(models.Model):
    PROJ_TASK_TYPES = (
        ('parser', 'Parser'), # Parsing domains from file data
        ('checker', 'Checker')) # Checking domains for a project
    project = models.ForeignKey(UserProject)
    celery_id = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=PROJ_TASK_TYPES)

# A single administrator-changeable settings
class AdminSetting(models.Model):
    FIELD_TYPES = (
        ('string', 'String'),
        ('integer', 'Number'),
        ('choice', 'Choice'),
        ('boolean', 'Boolean'),
        ('float', 'Float'))
    key = models.CharField(max_length=255, primary_key=True)
    value = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=FIELD_TYPES)
    choices = models.TextField(blank=True, null=True, default=None)

    @classmethod
    def get_value(cls, key):
        ads = AdminSetting.objects.get(key=key)
        if ads.type == 'integer':
            return int(ads.value)
        elif ads.type == 'boolean':
            return True if ads.value == 'true' else False
        elif ads.type == 'float':
            return float(ads.value)
        else:
            return ads.value

    # Test AccessID: moz-username
    # Test secret key: MOZ_API_KEY

    @classmethod
    def generate_moz_signature(cls, access_id, expires, key):
        # print access_id
        # print expires
        # print key
        return base64.b64encode(hmac.new(str(key), str('%s\n%s' % (access_id, expires)), hashlib.sha1).digest())
        
    @classmethod
    def get_moz_api_url(cls):
        if cls.get_value('use_live_moz_api'):
            return cls.get_value('live_moz_api_url')
        else:
            return cls.get_value('test_moz_api_url')

    @classmethod
    def get_moz_api_wait_time(cls):
        prefix = 'live_' if cls.get_value('use_live_moz_api') else 'test_'
        return cls.get_value(prefix+'moz_api_wait_time')

    @classmethod
    def get_moz_params(cls):
        prefix = 'test_'
        if AdminSetting.get_value('use_live_moz_api'):
            prefix = 'live_'
        access_id = cls.get_value(prefix+'moz_api_access_id')
        expires_str = str(time.time()+(60*10))
        secret_key = cls.get_value(prefix+'moz_api_secret_key')
        params=[
            ('AccessID', access_id),
            ('Expires', expires_str),
            ('Signature', cls.generate_moz_signature(access_id, expires_str, secret_key)),]
        print params
        return params

    @classmethod
    def get_api_params(cls):
        prefix = 'sandbox_'
        if AdminSetting.get_value('use_live_api'):
            prefix = 'live_'
        params=[
            ('ApiUser', AdminSetting.get_value(prefix+'api_user')),
            ('ApiKey', AdminSetting.get_value(prefix+'api_key')),
            ('UserName', AdminSetting.get_value(prefix+'api_username')),
            ('ClientIp', AdminSetting.get_value('client_ip'))]
        return params

    @classmethod
    def get_api_url(cls):
        if AdminSetting.get_value('use_live_api'):
            return AdminSetting.get_value('live_api_url')
        else:
            return AdminSetting.get_value('sandbox_api_url')
            
    @classmethod
    def get_api_wait_time(cls):
        if AdminSetting.get_value('use_live_api'):
            return AdminSetting.get_value('live_api_wait_time')
        else:
            return AdminSetting.get_value('sandbox_api_wait_time')

    @classmethod
    def get_api_urls_per_request(cls):
        if AdminSetting.get_value('use_live_api'):
            return AdminSetting.get_value('live_api_urls_per_request')
        else:
            return AdminSetting.get_value('sandbox_api_urls_per_request')

class MozLastUpdate(models.Model):
    datetime = models.DateTimeField()
    retrieved = models.DateTimeField()

    @classmethod
    def get_most_recent(cls):
        mr = MozLastUpdate.objects.all().order_by('-retrieved')
        if len(mr) == 0:
            return timezone.now()
        else:
            return mr[0].datetime

