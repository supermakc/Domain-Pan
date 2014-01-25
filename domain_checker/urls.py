from django.conf.urls import patterns, include, url
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'admin/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.MEDIA_ROOT+'admin/'}),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'admin/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.MEDIA_ROOT+'admin/'}),
    url(r'images/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.MEDIA_ROOT+'images/'}),
    url(r'css/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.MEDIA_ROOT+'css/'}),
    url(r'js/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.MEDIA_ROOT+'js/'}),
    url(r'fonts/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.MEDIA_ROOT+'fonts/'}),
    url(r'', include('main.urls')),
)
