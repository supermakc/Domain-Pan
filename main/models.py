from django.db import models
from django.contrib.auth.models import User

MAX_DOMAIN_LENGTH = 255

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
        ('parsing', 'Parsing domains'),
        ('checking', 'Checking domains'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('error', 'Error'))
    user = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=20, choices=PROJECT_STATES)
    error = models.TextField(blank=True, null=True, default=None)
    parse_errors = models.TextField(blank=True, null=True, default=None)
    updated = models.DateTimeField()

    def name(self):
        return self.uploadedfile_set.all()[0].filename

    def percent_complete(self):
        total_domains = len(self.projectdomain_set.all())*0.01
        checked_domains = len(self.projectdomain_set.filter(is_checked=True))
        return 100.0 if total_domains == 0 else checked_domains / total_domains

    def percent_complete_str(self):
        return '%.2f' % self.percent_complete()

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
