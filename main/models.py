from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models, transaction
from django.utils import timezone

import hmac, hashlib, base64, time, datetime

MAX_DOMAIN_LENGTH = 255

class URLMetrics(models.Model):
    """
    Moz API result for a single query URL.  See the Moz API documentation for information on what returned fields mean.

    .. note:

      Not all result fields may be filled; which ones are valid will depend on the data requested at the time of the API call.

    """
    query_url = models.CharField(max_length=MAX_DOMAIN_LENGTH)
    """The query URL of the check"""
    last_updated = models.DateTimeField(null=True, blank=True, default=None)
    """Date/time the URL was last checked"""
    extended_from = models.ForeignKey('self', null=True, blank=True, default=None)
    """If an extension of an existing metric result, this points to the original"""

    title = models.TextField(null=True, blank=True)
    """Title returned"""
    canonical_url = models.TextField(null=True, blank=True)
    """Canonical URL returned"""

    subdomain = models.CharField(max_length=MAX_DOMAIN_LENGTH, null=True, blank=True)
    """Subdomain returned"""
    root_domain = models.CharField(max_length=MAX_DOMAIN_LENGTH, null=True, blank=True)
    """Root domain returned"""
    external_links = models.FloatField(null=True, blank=True)
    """External links returned"""

    subdomain_external_links = models.IntegerField(null=True, blank=True)
    """Subdomain external links returned"""
    root_domain_external_links = models.IntegerField(null=True, blank=True)
    """Root domain external links returned"""
    equity_links = models.FloatField(null=True, blank=True)
    """Equity links returned"""

    subdomains_linking = models.IntegerField(null=True, blank=True)
    """Subdomains linking count returned"""
    root_domains_linking = models.IntegerField(null=True, blank=True)
    """Root domains linking count returned"""
    links = models.FloatField(null=True, blank=True)
    """Links count returned"""
    subdomain_subdomains_linking = models.IntegerField(null=True, blank=True)
    """Subdomains subdomains linking returned"""
    root_domain_root_domains_linking = models.IntegerField(null=True, blank=True)
    """Root domain root domains linking returned"""
    mozrank_10 = models.FloatField(null=True, blank=True)
    """MozRank (10-point normalized) returned"""
    mozrank_raw = models.FloatField(null=True, blank=True)
    """MozRank (raw) returned"""
    subdomain_mozrank_10 = models.FloatField(null=True, blank=True)
    """Subdomain MozRank (10-point normalized) returned"""
    subdomain_mozrank_raw = models.FloatField(null=True, blank=True)
    """Subdomain MozRank (raw) returned"""
    root_domain_mozrank_10 = models.FloatField(null=True, blank=True)
    """Root domain MozRank (10-point normalized) returned"""
    root_domain_mozrank_raw = models.FloatField(null=True, blank=True)
    """Root domain MozRank (raw) returned"""
    http_status_code = models.IntegerField(null=True, blank=True)
    """HTTP status code returned"""
    page_authority = models.FloatField(null=True, blank=True)
    """Page authority returned"""
    domain_authority = models.FloatField(null=True, blank=True)
    """Domain authority returned"""

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
    """Field name to Moz API call bitmask/code map"""

    def store_result(self, rd):
        """
        Stores the results of a Moz API call JSON result.

        Args:
          rd (dict): The JSON result in dictionary form.
        """
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
        """
        Returns whether this URL metric is up-to-date, i.e. whether Moz data has since been updated.
        """
        if self.last_updated is None:
            return False
        last_moz_update = MozLastUpdate.get_most_recent()
        return last_moz_update < self.last_updated

    @classmethod
    def create_cols_bitflag(cls, cols):
        """
        Returns a bitmask for use in a Moz API call based on a list of column names.

        Args:
          cols: List of columns to transform into a bitmask.
        """
        bf = 0
        for col in cols:
            bf |= cls.flag_map.get(col, ['', 0])[1]
        return bf


class TLD(models.Model):
    """
    A top-level domain.
    """
    domain = models.CharField(max_length=50)
    """Domain name"""
    is_recognized = models.BooleanField(default=False)
    """Whether the domain is recognized by the Namecheap API"""
    is_api_registerable = models.BooleanField(default=False)
    """Whether the domain can be registered through the Namecheap API"""
    description = models.CharField(max_length=255, blank=True, null=True, default=None)
    """Any associated description or other notes, as returned by the Namecheap API"""
    type = models.CharField(max_length=50)
    """Type of the domain, as listed by the Namecheap API"""

class ExcludedDomain(models.Model):
    """
    Top-level domain that should be automatically excluded (e.g. common domains like facebook.com, google.com)
    """
    domain = models.CharField(max_length=MAX_DOMAIN_LENGTH)
    """Domain name"""

class PreservedDomain(models.Model):
    """
    Top-level domain for which the subdomain portion should be preserved when parsing.
    """
    domain = models.CharField(max_length=MAX_DOMAIN_LENGTH)
    """Domain name"""

class UserProject(models.Model):
    """
    A project uploaded by a user.
    """
    PROJECT_STATES = (
        (u'parsing', u'Parsing domains'),
        (u'checking', u'Checking domains'),
        (u'measuring', u'Checking URL metrics'),
        (u'paused', u'Paused'),
        (u'completed', u'Completed'),
        (u'error', u'Error'))
    """Enumeration of recognized project states"""
    user = models.ForeignKey(User)
    """The user that uploaded this project"""
    created = models.DateTimeField(auto_now_add=True)
    """When the project was uploaded/created"""
    state = models.CharField(max_length=20, choices=PROJECT_STATES)
    """The current state of the project, one of PROJECT_STATES"""
    error = models.TextField(blank=True, null=True, default=None)
    """If the project encountered a fatal error, this field contains a text description of the error"""
    parse_errors = models.TextField(blank=True, null=True, default=None)
    """An aggregated list of errors encountered when parsing (non-fatal)"""
    creation_datetime = models.DateTimeField(blank=True, auto_now_add=True)
    """Date/time the project was created"""
    completed_datetime = models.DateTimeField(blank=True, null=True)
    """Date/time the project was completed or encountered a fatal error"""
    completion_email_sent = models.BooleanField(default=False)
    """Whether a notification email has yet been sent to the user indicating completion/failure"""
    last_updated = models.DateTimeField(null=True, blank=True, default=None)
    """Date/time the project data was last updated"""
    urlmetrics = models.ManyToManyField(URLMetrics, through='ProjectMetrics')
    """Association with available URL metrics"""

    def name(self):
        """
        Returns the name of the project (currently the filename of the uploaded file).
        """
        return self.uploadedfile_set.all()[0].filename

    def send_completion_email(self):
        """
        Send a completion email formatted for this project.
        """
        reply_address = AdminSetting.get_value(u'noreply_address')
        server_address = AdminSetting.get_value(u'server_address')
        messagebody = (u'The project "%s" has successfully completed.  You can view the results at the following address:\n\n' + \
                      u'%s/project?id=%d\n\n' + \
                      u'Thank you for using Domain Checker.') % (self.name(), server_address, self.id)
        send_mail(u'Domain Checker - Project "%s" complete' % (self.name()), messagebody, reply_address, [self.user.email])

    def get_measurable_domains(self):
        """
        Returns the number of associations with URL metrics.
        """
        return self.urlmetrics.all()

    def get_measured_domains(self):
        """
        Returns the list of associated URL metrics that have been checked.
        """
        return URLMetrics.objects.filter(projectmetrics__project=self, projectmetrics__is_checked=True)

    def get_percent_complete(self):
        """
        Returns a float percentage estimate of the project progress based on how many domains have been checked for availability and/or measured.
        """
        checkable_domains = len(self.projectdomain_set.all())
        checked_domains = len(self.projectdomain_set.filter(is_checked=True))

        measurable_domains = len(self.get_measurable_domains())
        measured_domains = len(self.get_measured_domains())

        completed_domains = checked_domains + measured_domains
        total_domains = checkable_domains + measurable_domains

        return 100.0 if total_domains == 0 else (completed_domains*100.0) / total_domains

    def get_percent_complete_display(self):
        """
        Returns the project completion estimate in string form with two decimal places.
        """
        return '%.2f' % self.get_percent_complete

    def is_running(self):
        """
        Returns whether the project is still running.
        """
        return self.state not in ['completed', 'paused', 'error']

    def all_checked(self):
        """
        Returns whether all this project's domains have been availability checked.
        """
        return self.projectdomain_set.filter(is_checked=False)).count() == 0

    def all_measured(self):
        """
        Returns whether all applicable domains for this project have had their metrics collected.
        """
        return self.projectmetrics_set.filter(is_checked=False)).count() == 0

    def update_state(self, save=True):
        """
        Sets the project state according to how many domains have been availability checked and/or metric measured (also takes into account errors.
        """
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
        """
        Returns the total run-time of the project (to date if not complete).
        """
        if not self.is_running():
            if self.completed_datetime is None:
                return 'error'
            return str(self.completed_datetime - self.creation_datetime)
        else:
            return str(timezone.now() - self.creation_datetime)

class ProjectMetrics(models.Model):
    """
    Join/association that relates projects to URL metrics.
    """
    project = models.ForeignKey(UserProject)
    """The project"""
    urlmetrics = models.ForeignKey(URLMetrics)
    """The URL metric associated with the project"""
    is_checked = models.BooleanField(default=False)
    """Whether the URL metric has been updated/checked for this particular project"""
    is_extension = models.BooleanField(default=False)
    """Whether this association represents an 'extension', i.e. the addition of 'www.' to an existing URL metric"""
    
class UploadedFile(models.Model):
    """
    Uploaded project file.
    """
    project = models.ForeignKey(UserProject)
    """The project for which the file was uploaded"""
    filename = models.CharField(max_length=255)
    """File's name"""
    filedata = models.TextField()
    """The contents of the file, stored as raw text"""

class ProjectDomain(models.Model):
    """
    Domain to be checked for a project.
    """
    DOMAIN_STATES = (
        ('unchecked', 'Unchecked'),
        ('unregisterable', 'Unregisterable'),
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
        ('special', 'Special/Preserved'),
        ('error', 'Error'))
    """Enumeration of recognized domain states"""
    project = models.ForeignKey(UserProject)
    """The project"""
    domain = models.CharField(max_length=MAX_DOMAIN_LENGTH)
    """The domain name to be checked"""
    original_link = models.TextField()
    """The original full link from which the domain was parsed"""
    subdomains_preserved = models.BooleanField()
    """Whether this domain had its subdomains preserved when parsed"""
    is_checked = models.BooleanField()
    """Whether the domain has been checked for the project"""
    state = models.CharField(max_length=20, choices=DOMAIN_STATES)
    """The state of the domain, one of DOMAIN_STATES"""
    error = models.TextField(blank=True, null=True, default=None)
    """If an error has occurred, a text message descriptor of the error"""
    last_checked = models.DateTimeField()
    """Date/time the domain was checked"""

class ProjectTask(models.Model):
    """
    A background(Celery) task for a project.

    .. note::
      
      This was intended for internal tracking of celery tasks, but is not currently used.

    """
    PROJ_TASK_TYPES = (
        ('parser', 'Parser'), # Parsing domains from file data
        ('checker', 'Checker'),
        ('metrics', 'Metrics')) # Checking domains for a project
    """Enumeration of project types"""
    project = models.ForeignKey(UserProject)
    """The project"""
    celery_id = models.CharField(max_length=255)
    """The Celery ID of the task"""
    type = models.CharField(max_length=20, choices=PROJ_TASK_TYPES)
    """The type of task, one of PROJ_TASK_TYPES"""

# A single administrator-changeable settings
class AdminSetting(models.Model):
    FIELD_TYPES = (
        ('string', 'String'),
        ('integer', 'Number'),
        ('choice', 'Choice'),
        ('boolean', 'Boolean'),
        ('float', 'Float'))
    """Enumeration of possible field types"""
    key = models.CharField(max_length=255, primary_key=True)
    """Name of the setting field"""
    value = models.CharField(max_length=255)
    """Field value"""
    type = models.CharField(max_length=20, choices=FIELD_TYPES)
    """Field data type, one of FIELD_TYPES"""
    choices = models.TextField(blank=True, null=True, default=None)
    """If of the 'choice' data type, a comma-separated list of possible choices"""

    @classmethod
    def get_value(cls, key):
        """
        Returns the value for the given key as the corrent data type.
        """
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
    def generate_moz_signature(cls, access_id, expires, key):
        """
        Returns the correctly encoded Moz API call key for the given values.

        Args:
          access_id (str): Access ID of the Moz API registered user.
          expires (str): UNIX time at which the call should expire.
          key (str): Access key for the Moz API registered user.
        """
        return base64.b64encode(hmac.new(str(key), str('%s\n%s' % (access_id, expires)), hashlib.sha1).digest())
        
    @classmethod
    def get_moz_api_url(cls):
        """
        Returns the set Moz API call URL (i.e. live or test).
        """
        if cls.get_value('use_live_moz_api'):
            return cls.get_value('live_moz_api_url')
        else:
            return cls.get_value('test_moz_api_url')

    @classmethod
    def get_moz_api_wait_time(cls):
        """
        Returns the set Moz API call wait interval (i.e. live or test).
        """
        prefix = 'live_' if cls.get_value('use_live_moz_api') else 'test_'
        return cls.get_value(prefix+'moz_api_wait_time')

    @classmethod
    def get_moz_params(cls):
        """
        Returns a list of parameters for a Moz API call that reflects all current settings (i.e. live or test).
        """
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
        # print params
        return params

    @classmethod
    def get_api_params(cls):
        """
        Returns a list of parameters for NameCheap API call that reflects all current settings (i.e. live or test).
        """
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
        """
        Returns the currently set Namecheap API call URL (i.e. live or test).
        """
        if AdminSetting.get_value('use_live_api'):
            return AdminSetting.get_value('live_api_url')
        else:
            return AdminSetting.get_value('sandbox_api_url')
            
    @classmethod
    def get_api_wait_time(cls):
        """
        Returns the currently set Namecheap API call wait interval (i.e. live or test).
        """
        if AdminSetting.get_value('use_live_api'):
            return AdminSetting.get_value('live_api_wait_time')
        else:
            return AdminSetting.get_value('sandbox_api_wait_time')

    @classmethod
    def get_api_urls_per_request(cls):
        """
        Returns the currently set limit of URLs in a single Namecheap API call (i.e. live or test).
        """
        if AdminSetting.get_value('use_live_api'):
            return AdminSetting.get_value('live_api_urls_per_request')
        else:
            return AdminSetting.get_value('sandbox_api_urls_per_request')

class MozLastUpdate(models.Model):
    """
    A record of a call the Moz API to check when the Moz data was last updated.  This is used to check whether existing URL metrics need to be updated.
    """
    datetime = models.DateTimeField()
    retrieved = models.DateTimeField()

    @classmethod
    def get_most_recent(cls):
        """
        Returns the date/time of the most recent update.
        """
        mr = MozLastUpdate.objects.all().order_by('-retrieved')
        if len(mr) == 0:
            return timezone.now()
        else:
            return mr[0].datetime

