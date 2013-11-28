from django.db import models
from django.contrib.auth.models import User

MAX_DOMAIN_LENGTH = 255

# Top-level domains
class TLD(models.Model):
    domain = models.CharField(max_length=50)
    is_recognized = models.BooleanField(default=False)
    is_api_registerable = models.BooleanField(default=False)
    description = models.CharField(max_length=255, null=True, default=None)
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
    error = models.TextField(null=True)
    updated = models.DateTimeField()

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
    error = models.TextField(null=True)
    last_checked = models.DateTimeField()

# Association between projects and background(Celery) tasks
class ProjectTask(models.Model):
    PROJ_TASK_TYPES = (
        ('parser', 'Parser'), # Parsing domains from file data
        ('checker', 'Checker')) # Checking domains for a project
    project = models.ForeignKey(UserProject)
    celery_id = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=PROJ_TASK_TYPES)


