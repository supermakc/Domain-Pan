# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ExtensionPrefix'
        db.create_table(u'main_extensionprefix', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('prefix', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal(u'main', ['ExtensionPrefix'])


    def backwards(self, orm):
        # Deleting model 'ExtensionPrefix'
        db.delete_table(u'main_extensionprefix')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'main.adminsetting': {
            'Meta': {'object_name': 'AdminSetting'},
            'choices': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'primary_key': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'main.excludeddomain': {
            'Meta': {'object_name': 'ExcludedDomain'},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'main.extensionprefix': {
            'Meta': {'object_name': 'ExtensionPrefix'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'prefix': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'main.mozlastupdate': {
            'Meta': {'object_name': 'MozLastUpdate'},
            'datetime': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'retrieved': ('django.db.models.fields.DateTimeField', [], {})
        },
        u'main.preserveddomain': {
            'Meta': {'object_name': 'PreservedDomain'},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'main.projectdomain': {
            'Meta': {'object_name': 'ProjectDomain'},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'error': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_checked': ('django.db.models.fields.BooleanField', [], {}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {}),
            'original_link': ('django.db.models.fields.TextField', [], {}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['main.UserProject']"}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'subdomains_preserved': ('django.db.models.fields.BooleanField', [], {})
        },
        u'main.projectmetrics': {
            'Meta': {'object_name': 'ProjectMetrics'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_checked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_extension': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['main.UserProject']"}),
            'urlmetrics': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['main.URLMetrics']"})
        },
        u'main.projecttask': {
            'Meta': {'object_name': 'ProjectTask'},
            'celery_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['main.UserProject']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'main.tld': {
            'Meta': {'object_name': 'TLD'},
            'description': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_api_registerable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_recognized': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'main.uploadedfile': {
            'Meta': {'object_name': 'UploadedFile'},
            'filedata': ('django.db.models.fields.TextField', [], {}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['main.UserProject']"})
        },
        u'main.urlmetrics': {
            'Meta': {'object_name': 'URLMetrics'},
            'canonical_url': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain_authority': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'equity_links': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'extended_from': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['main.URLMetrics']", 'null': 'True', 'blank': 'True'}),
            'external_links': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'http_status_code': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'links': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'mozrank_10': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'mozrank_raw': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'page_authority': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'query_url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'root_domain': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'root_domain_external_links': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'root_domain_mozrank_10': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'root_domain_mozrank_raw': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'root_domain_root_domains_linking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'root_domains_linking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subdomain': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'subdomain_external_links': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subdomain_mozrank_10': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'subdomain_mozrank_raw': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'subdomain_subdomains_linking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subdomains_linking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'main.userproject': {
            'Meta': {'object_name': 'UserProject'},
            'completed_datetime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'completion_email_sent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creation_datetime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'error': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'parse_errors': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'urlmetrics': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['main.URLMetrics']", 'through': u"orm['main.ProjectMetrics']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['main']