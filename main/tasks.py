from __future__ import absolute_import
from xml.etree import ElementTree
import copy, time

from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone
from main.models import ProjectDomain, UserProject
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
        'ClientIp' : LOCAL_IP,
        'command' : 'namecheap.domains.check',
        'DomainList' : '',}

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
    # print rstring
    tree = ElementTree.fromstring(rstring)
    raw_results = tree.findall('./{http://api.namecheap.com/xml.response}CommandResponse/{http://api.namecheap.com/xml.response}DomainCheckResult')
    result_list = []
    for result in raw_results:
        result_list.append({
            'domain' : result.attrib['Domain'],
            'available' : bool(result.attrib['Available']),
            'errorno' : int(result.attrib['ErrorNo']),
            'description' : result.attrib['Description'],})
    return result_list

@app.task
def check_project_domains(project_id):
    # domain_list = ProjectDomain.objects.filter(project=project_id, is_checked=False)
    # print len(domain_list)

    while True:
        while not cache.add(NAMECHEAP_LOCK_ID, 'true', MINIMUM_WAIT_TIME):
            pass
        domain_list = ProjectDomain.objects.filter(project=project_id, is_checked=False)[:URLS_PER_REQUEST]
        if len(domain_list) == 0:
            project = UserProject.objects.get(id=project_id)
            project.is_complete = True
            project.updated = timezone.now()
            project.save()
            break

        domain_str = ','.join([pd.domain for pd in domain_list])
        params = copy.deepcopy(NAMECHEAP_PARAMS)
        params['DomainList'] = domain_str
        print domain_str
        r = requests.get(NAMECHEAP_API_URL, params=params)
        rxml = r.text
        results = parse_namecheap_result(rxml)
        for result in results:
            i = 0
            print result['domain']
            if result['domain'] == domain_list[i].domain:
                domain_list[i].is_available = result['available']
                break
            else:
                i += 1

        # TODO: Remaining domains throw errors, but we ignore these for now
        for domain in domain_list:
            domain.is_checked = True
            domain.last_checked = timezone.now()
            domain.save()

        cache.delete(NAMECHEAP_LOCK_ID)
        # break


