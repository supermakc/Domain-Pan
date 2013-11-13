from __future__ import absolute_import
from xml.etree import ElementTree
from multiprocessing import Lock
import copy, time

from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from main.models import ProjectDomain, UserProject, UploadedFile
from django.contrib.auth.models import User
from django.core.cache import cache

from domain_checker.celery import app
import requests

NAMECHEAP_LOCK_ID = 'namecheap-lock'
MINIMUM_WAIT_TIME = 30 # seconds
URLS_PER_REQUEST = 20

LOCAL_IP = '127.0.0.1'
TESTSERVER_IP = '127.0.0.1'

NAMECHEAP_API_URL = 'https://api.sandbox.namecheap.com/xml.response'
NAMECHEAP_PARAMS = {
        'ApiUser' : 'username',
        'ApiKey' : 'NAMECHEAP_API_KEY',
        'UserName' : 'username',
        'ClientIp' : TESTSERVER_IP,
        'command' : 'namecheap.domains.check',
        'DomainList' : '',}

namecheap_lock = Lock()

@app.task
def add(x, y):
    return x + y

@app.task
def mul(x, y):
    return x * y

@app.task
def xsum(numbers):
    return sum(numbers)

def parse_namecheap_result(rstring):
    print rstring
    tree = ElementTree.fromstring(rstring)
    raw_results = tree.findall('./{http://api.namecheap.com/xml.response}CommandResponse/{http://api.namecheap.com/xml.response}DomainCheckResult')
    result_list = []
    for result in raw_results:
        result_list.append({
            'domain' : result.attrib['Domain'],
            'available' : bool(result.attrib['Available']),
            'errorno' : int(result.attrib['ErrorNo']),
            'description' : result.attrib['Description'],})

    for result in result_list:
        print result

    return result_list

@app.task
def check_project_domains(project_id):
    # domain_list = ProjectDomain.objects.filter(project=project_id, is_checked=False)
    # print len(domain_list)

    while True:
        namecheap_lock.acquire()
        """
        while not cache.add(NAMECHEAP_LOCK_ID, 'true', MINIMUM_WAIT_TIME*4):
            pass
        """
        domain_list = ProjectDomain.objects.filter(project=project_id, is_checked=False)[:URLS_PER_REQUEST]
        if len(domain_list) == 0:
            project = UserProject.objects.get(id=project_id)
            project.is_complete = True
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
            namecheap_lock.release()
            # cache.delete(NAMECHEAP_LOCK_ID)
            break

        domain_str = ','.join([pd.domain for pd in domain_list])
        params = copy.deepcopy(NAMECHEAP_PARAMS)
        params['DomainList'] = domain_str
        print domain_str
        r = requests.get(NAMECHEAP_API_URL, params=params)
        rxml = r.text
        results = parse_namecheap_result(rxml)
        for result in results:
            print 'Finding match for "%s"...' % (result['domain'])
            for domain in domain_list:
                if result['domain'] == domain.domain:
                    print '   Match found with domain name "%s"' % (domain.domain)
                    domain.is_available = result['available']
                    break

        # TODO: Remaining domains throw errors, but we ignore these for now
        for domain in domain_list:
            domain.is_checked = True
            domain.last_checked = timezone.now()
            domain.save()

        time.sleep(MINIMUM_WAIT_TIME)
        namecheap_lock.release()
        # cache.delete(NAMECHEAP_LOCK_ID)
        # break


