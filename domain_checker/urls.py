from django.conf.urls import patterns, include, url
from django.conf import settings

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'domain_checker.views.home', name='home'),
    # url(r'^domain_checker/', include('domain_checker.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    url(r'', include('main.urls')),
    url(r'admin/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.MEDIA_ROOT+'admin/'}),
    url(r'css/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.MEDIA_ROOT+'css/'}),
    url(r'js/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.MEDIA_ROOT+'js/'}),
    url(r'fonts/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.MEDIA_ROOT+'fonts/'}),
)
