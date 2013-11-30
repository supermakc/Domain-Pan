# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TLD'
        db.create_table(u'main_tld', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('domain', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('is_recognized', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_api_registerable', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('description', self.gf('django.db.models.fields.CharField')(default=None, max_length=255, null=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal(u'main', ['TLD'])

        # Adding model 'ExcludedDomain'
        db.create_table(u'main_excludeddomain', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('domain', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal(u'main', ['ExcludedDomain'])

        # Adding model 'PreservedDomain'
        db.create_table(u'main_preserveddomain', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('domain', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal(u'main', ['PreservedDomain'])

        # Adding model 'UserProject'
        db.create_table(u'main_userproject', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('error', self.gf('django.db.models.fields.TextField')(null=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal(u'main', ['UserProject'])

        # Adding model 'UploadedFile'
        db.create_table(u'main_uploadedfile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.UserProject'])),
            ('filename', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('filedata', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'main', ['UploadedFile'])

        # Adding model 'ProjectDomain'
        db.create_table(u'main_projectdomain', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.UserProject'])),
            ('domain', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('original_link', self.gf('django.db.models.fields.TextField')()),
            ('subdomains_preserved', self.gf('django.db.models.fields.BooleanField')()),
            ('is_checked', self.gf('django.db.models.fields.BooleanField')()),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('error', self.gf('django.db.models.fields.TextField')(null=True)),
            ('last_checked', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal(u'main', ['ProjectDomain'])

        # Adding model 'ProjectTask'
        db.create_table(u'main_projecttask', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.UserProject'])),
            ('celery_id', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal(u'main', ['ProjectTask'])

        # Adding model 'AdminSetting'
        db.create_table(u'main_adminsetting', (
            ('key', self.gf('django.db.models.fields.CharField')(max_length=255, primary_key=True)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('choices', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'main', ['AdminSetting'])


    def backwards(self, orm):
        # Deleting model 'TLD'
        db.delete_table(u'main_tld')

        # Deleting model 'ExcludedDomain'
        db.delete_table(u'main_excludeddomain')

        # Deleting model 'PreservedDomain'
        db.delete_table(u'main_preserveddomain')

        # Deleting model 'UserProject'
        db.delete_table(u'main_userproject')

        # Deleting model 'UploadedFile'
        db.delete_table(u'main_uploadedfile')

        # Deleting model 'ProjectDomain'
        db.delete_table(u'main_projectdomain')

        # Deleting model 'ProjectTask'
        db.delete_table(u'main_projecttask')

        # Deleting model 'AdminSetting'
        db.delete_table(u'main_adminsetting')


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
            'choices': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'primary_key': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'main.excludeddomain': {
            'Meta': {'object_name': 'ExcludedDomain'},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'main.preserveddomain': {
            'Meta': {'object_name': 'PreservedDomain'},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'main.projectdomain': {
            'Meta': {'object_name': 'ProjectDomain'},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_checked': ('django.db.models.fields.BooleanField', [], {}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {}),
            'original_link': ('django.db.models.fields.TextField', [], {}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['main.UserProject']"}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'subdomains_preserved': ('django.db.models.fields.BooleanField', [], {})
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
            'description': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True'}),
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
        u'main.userproject': {
            'Meta': {'object_name': 'UserProject'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['main']