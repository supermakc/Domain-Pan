from django.db import models
from django.contrib.auth.models import User

MAX_DOMAIN_LENGTH = 255

# Top-level domains
class TLD(models.Model):
    domain = models.CharField(max_length=50)
    included = models.BooleanField()

# Domains that will be excluded from availability checks
class ExcludedDomain(models.Model):
    domain = models.CharField(max_length=MAX_DOMAIN_LENGTH)

# Domains for which subdomains are preserved
class PreservedDomain(models.Model):
    domain = models.CharField(max_length=MAX_DOMAIN_LENGTH)

# User projects
class UserProject(models.Model):
    user = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    is_complete = models.BooleanField()
    is_paused = models.BooleanField()
    updated = models.DateTimeField()

# Uploaded project files
class UploadedFile(models.Model):
    filename = models.CharField(max_length=255)
    filedata = models.TextField()
    project = models.ForeignKey(UserProject)

# Unique domains calculated for user projects
class ProjectDomain(models.Model):
    domain = models.CharField(max_length=MAX_DOMAIN_LENGTH)
    subdomains_preserved = models.BooleanField()
    is_checked = models.BooleanField()
    last_checked = models.DateTimeField()
    is_available = models.BooleanField()
    project = models.ForeignKey(UserProject)
