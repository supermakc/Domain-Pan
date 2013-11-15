from django.contrib import admin
from django.contrib.auth.models import User
from main.models import UserProject, ProjectDomain, UploadedFile

# Register your models here.

class UserProjectAdmin(admin.ModelAdmin):
    list_display = ('filename', 'username', 'last_updated', 'num_domains', 'is_complete')
    list_filter = ('user',)

    def filename(self, obj):
        return UploadedFile.objects.get(project_id=obj.id).filename

    def username(self, obj):
        return User.objects.get(id=obj.user_id).username

    def last_updated(self, obj):
        return obj.updated

    def num_domains(self, obj):
        return len(ProjectDomain.objects.filter(project_id=obj.id))

    def is_complete(self, obj):
        return obj.is_complete

class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'username', 'length', 'num_domains')

    def filename(self, obj):
        return obj.filename

    def username(self, obj):
        return User.objects.get(id=UserProject.objects.get(id=obj.project_id).user_id).username

    def length(self, obj):
        return len(obj.filedata)

    def num_domains(self, obj):
        return len(ProjectDomain.objects.filter(project_id=UserProject.objects.get(id=obj.project_id).id))

admin.site.register(UserProject, UserProjectAdmin)
# admin.site.register(ProjectDomain)
admin.site.register(UploadedFile, UploadedFileAdmin)
