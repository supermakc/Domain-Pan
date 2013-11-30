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
    r = requests.get(AdminSetting.get_api_url(), params=params)

    rtext = r.text
    print rtext

    # send_mail('Domain Checker - Project "%s" complete' % (pfile.filename), messagebody, reply_address, [user.email])
    send_mail('Domain Checker - TLD Update', 'The following response was received from the TLD update (using %s):\n\n%s' % (AdminSetting.get_api_url(), rtext), AdminSetting.get_value('noreply_address'), [AdminSetting.get_value('admin_address')])

    rtree = ElementTree.fromstring(rtext)
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

        for ncd, rel in rels.items():
            if len(TLD.objects.filter(domain=ncd)) == 0:
                new_tld = TLD(domain=ncd, is_recognized=True, is_api_registerable=(rel.attrib['IsApiRegisterable'] == True), description=rel.text, type=rel.attrib['Type'])
                new_tld.save()
                print 'New TLD added: %s' % ncd

    print 'Finished processing tlds.'

def parse_namecheap_result(rstring):
    print rstring
    tree = ElementTree.fromstring(rstring)
    check_raw = tree.findall('./{http://api.namecheap.com/xml.response}CommandResponse/{http://api.namecheap.com/xml.response}DomainCheckResult')
    error_raw = tree.findall('./{http://api.namecheap.com/xml.response}Errors/{http://api.namecheap.com/xml.response}Error')

    domain_results = []
    for check in check_raw:
        domain_results.append({
            'domain' : check.attrib['Domain'],
            'available' : (check.attrib['Available'] == 'true'),
            'errorno' : int(check.attrib['ErrorNo']),
            'description' : check.attrib['Description']})

    for result in domain_results:
        print result

    error_results = []
    for error in error_raw:
        error_results.append({
            'number' : error.attrib['Number'],
            'description' : error.text})

    return (domain_results, error_results)

@app.task
def check_project_domains(project_id):
    lock = NamecheapLock()
    project = UserProject.objects.get(id=project_id)
    if settings.DEBUG:
        logging.basicConfig() 
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
    while True:
        lock.acquire()
        try:
            domain_list = project.projectdomain_set.filter(is_checked=False)[:AdminSetting.get_api_urls_per_request()]
            if len(domain_list) == 0:
                project = UserProject.objects.get(id=project_id)
                project.state = 'completed'
                project.updated = timezone.now()
                project.save()

                pfile = UploadedFile.objects.get(project_id=project.id)
                reply_address = AdminSetting.get_value('noreply_address')
                server_address = AdminSetting.get_value('server_address')
                messagebody = ('The project "%s" has successfully completed.  You can view the results at the following address:\n\n' + \
                              '%s/project?id=%d\n\n' + \
                              'Thank you for using Domain Checker.') % (pfile.filename, server_address, project.id)
                user = User.objects.get(id=project.user_id)
                send_mail('Domain Checker - Project "%s" complete' % (pfile.filename), messagebody, reply_address, [user.email])
                lock.release()
                break

            domains = dict([(d.domain, d) for d in domain_list])
            domain_str = ','.join(domains.keys())

            params = AdminSetting.get_api_params()
            params.append(('Command', 'namecheap.domains.check'))
            params.append(('DomainList', domain_str))

            print domain_str
            print params
            r = requests.get(AdminSetting.get_api_url(), params=params)
            # print r.url
            # print r.headers
            sc = r.status_code
            print 'Status code: %d' % sc

            if sc == 200:
                rxml = r.text
                (domain_results, error_results) = parse_namecheap_result(rxml)
                for dr in domain_results:
                    print 'Finding match for "%s"...' % (dr['domain'])
                    if domains.has_key(dr['domain']):
                        d = domains[dr['domain']]
                        if dr['errorno'] != 0:
                            d.state = 'error'
                            d.description = dr['description']
                        else:
                            d.state = 'available' if dr['available'] else 'unavailable'
                            d.description = None
                        d.is_checked = True
                        d.last_checked = timezone.now()
                        d.save()

                for domain, d in domains.items():
                    if d.state == 'unchecked':
                        print 'Domain result not found (will recheck later): %s' % domain
            else:
                print 'Warning: Unexpected response while calling API code: %d, will retry after delay' % sc

            time.sleep(AdminSetting.get_api_wait_time())
            lock.release()
        except Exception as e:
            lock.release()
            project.state = 'error'
            project.error = 'Error occurred while checking domains: %s' % str(e)
            project.save()
            reply_address = AdminSetting.get_value('noreply_address')
            server_address = AdminSetting.get_value('server_address')
            messagebody = ('The project "%s" has encountered an error:\n\n  %s\n\nYou can view the results at the following address:\n\n' + \
                          '%s/project?id=%d\n\n' + \
                          'Thank you for using Domain Checker.') % (project.name(), project.error, server_address, project.id)
            user = User.objects.get(id=project.user_id)
            send_mail('Domain Checker - Project "%s" Error' % (project.name(),), messagebody, reply_address, [user.email])
            # Propagate error to Celery handler
            raise


