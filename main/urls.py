from django.conf.urls import patterns, url

from main import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^login$', views.check_login, name='check_login'),
    url(r'^profile$', views.profile, name='profile'),
    url(r'logout_user$', views.logout_user, name='logout_user'),
    url(r'change_details$', views.change_details, name='change_details'),
    url(r'change_password$', views.change_password, name='change_password'),
    url(r'change_email$', views.change_email, name='change_email'),
    url(r'delete_project$', views.delete_project, name='delete_project'),
    url(r'update_admin$', views.update_admin, name='update_admin'),
    url(r'register_user$', views.register_user, name='register_user'),
    url(r'upload_project$', views.upload_project, name='upload_project'))
