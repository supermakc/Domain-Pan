from django.conf.urls import patterns, url, include
from django.contrib import admin
admin.autodiscover()

from main import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^admin/', include(admin.site.urls)), 
    url(r'^login$', views.check_login, name='check_login'),
    url(r'^profile$', views.profile, name='profile'),
    url(r'^project_list$', views.project_list, name='project_list'),
    url(r'^logout_user$', views.logout_user, name='logout_user'),
    url(r'^change_details$', views.change_details, name='change_details'),
    url(r'^change_password$', views.change_password, name='change_password'),
    url(r'^change_email$', views.change_email, name='change_email'),
    url(r'^delete_project$', views.delete_project, name='delete_project'),
    url(r'^update_admin$', views.update_admin, name='update_admin'),
    url(r'^register_user$', views.register_user, name='register_user'),
    url(r'^check_username$', views.check_username, name='check_username'),
    url(r'^reset_user$', views.reset_user, name='reset_user'),
    url(r'^update_tlds$', views.manual_update_tlds, name='update_tlds'),
    url(r'^update_metrics$', views.manual_update_metrics, name='update_metrics'),
    url(r'^update_states$', views.manual_update_states, name='upload_states'),
    url(r'^project$', views.project, name='project'),
    url(r'^admin_settings/$', views.admin_settings, name='admin_settings'),
    url(r'^upload_project$', views.upload_project, name='upload_project'))
