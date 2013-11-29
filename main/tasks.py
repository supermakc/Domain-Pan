from __future__ import absolute_import
from xml.etree import ElementTree
import os, copy, time, logging, json, tempfile, sqlite3

from django.db import transaction
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.core.cache import cache

from domain_checker.celery import app
from main.models import ProjectDomain, UserProject, UploadedFile, TLD, AdminSetting

import requests, lockfile

NAMECHEAP_LOCK_ID = 'namecheap-lock'
NAMECHEAP_PARAMS = [
    ('ApiUser', settings.NAMECHEAP_API_USER),
    ('ApiKey', settings.NAMECHEAP_API_KEY),
    ('UserName', settings.NAMECHEAP_API_USERNAME),
    ('ClientIp', settings.NAMECHEAP_IP),
]

# TODO: Deal with stale locks
class NamecheapLock():
    def __init__(self):
        self.lockfile = lockfile.FileLock(os.path.join(tempfile.gettempdir(), 'namecheap'))

    def acquire(self):
        self.lockfile.acquire()

    def release(self):
        self.lockfile.release()

@app.task
def update_tlds():
    params = AdminSetting.get_api_params()
    params.append(('Command', 'namecheap.domains.gettldlist'))
    r = requests.get(AdminSettings.get_api_url(), params=params)

    rtree = ElementTree.fromstring(r.text)
    rels = rtree.findall('./{http://api.namecheap.com/xml.response}CommandResponse/{http://api.namecheap.com/xml.response}Tlds/{http://api.namecheap.com/xml.response}Tld')

    rels = dict([(r.attrib['Name'], r) for r in rels])
    tlds = TLD.objects.all()
    with transaction.atomic():
        for tld in tlds:
            if tld.domain in rels.keys():
                rel = rels[tld.domain]
                tld.is_recognized = True
                tld.is_api_registerable = (rel.attrib['IsApiRegisterable'] == 'true')
                tld.description = rel.text
                tld.type = rel.attrib['Type']
            else:
                tld.is_recognized = False
                tld.is_api_registrable = False
                tld.type = 'unknown'
                tld.description = None
            tld.save()

    print 'Finished processing tlds.'

def parse_namecheap_result(rstring):
    print rstring
    tree = ElementTree.fromstring(rstring)
    raw_results = tree.findall('./{http://api.namecheap.com/xml.response}CommandResponse/{http://api.namecheap.com/xml.response}DomainCheckResult')
    result_list = []
    for result in raw_results:
        result_list.append({
            'domain' : result.attrib['Domain'],
            'available' : result.attrib['Available'] == 'true',
            'errorno' : int(result.attrib['ErrorNo']),
            'description' : result.attrib['Description'],})

    for result in result_list:
        print result

    return result_list

@app.task
def check_project_domains(project_id):
    lock = NamecheapLock()
    if settings.DEBUG:
        logging.basicConfig() 
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
    while True:
        lock.acquire()
        try:
            domain_list = ProjectDomain.objects.filter(project=project_id, is_checked=False)[:AdminSetting.get_api_urls_per_request()]
            if len(domain_list) == 0:
                project = UserProject.objects.get(id=project_id)
                project.state = 'completed'
                project.updated = timezone.now()
                project.save()

                pfile = UploadedFile.objects.get(project_id=project.id)
                reply_address = 'noreply@domain.com'
                server_address = 'http://dc.domain.com'
                messagebody = ('The project "%s" has successfully completed.  You can view the results at the following address:\n\n' + \
                              '%s/project?id=%d\n\n' + \
                              'Thank you for using Domain Checker.') % (pfile.filename, server_address, project.id)
                user = User.objects.get(id=project.user_id)
                send_mail('Domain Checker - Project "%s" complete' % (pfile.filename), messagebody, reply_address, [user.email])
                lock.release()
                break

            domain_str = ','.join([pd.domain for pd in domain_list])
            params = AdminSetting.get_api_params()
            params.append(('Command', 'namecheap.domains.check'))
            params.append(('DomainList', domain_str))
            print domain_str
            print params
            r = requests.get(AdminSetting.get_api_url(), params=params)
            print r.url
            print r.headers
            rxml = r.text
            results = parse_namecheap_result(rxml)
            for result in results:
                print 'Finding match for "%s"...' % (result['domain'])
                for domain in domain_list:
                    if result['domain'] == domain.domain:
                        print '   Match found with domain name "%s"' % (domain.domain)
                        domain.state = 'available' if result['available'] else 'unavailable'
                        break

            # TODO: Remaining domains throw errors, but we ignore these for now
            for domain in domain_list:
                if domain.state == 'unchecked':
                    domain.state = 'error'
                    domain.error = 'Unable to determine TLD'
                domain.is_checked = True
                domain.last_checked = timezone.now()
                domain.save()

            time.sleep(AdminSetting.get_api_wait_time())
            lock.release()
        except Exception as e:
            lock.release()
            raise


