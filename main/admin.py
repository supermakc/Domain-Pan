from django.contrib import admin
from main.models import UserProject, ProjectDomain, UploadedFile

# Register your models here.
admin.site.register(UserProject)
admin.site.register(ProjectDomain)
admin.site.register(UploadedFile)
