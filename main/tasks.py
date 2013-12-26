from __future__ import absolute_import
from lxml import etree
import sys, os, copy, time, logging, json, tempfile, sqlite3, traceback

from django.db import transaction
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.core.cache import cache

from domain_checker.celery import app
from main.models import ProjectDomain, UserProject, UploadedFile, TLD, AdminSetting, ProjectTask, URLMetrics, MozLastUpdate

import requests, lockfile, datetime

NAMECHEAP_LOCK_ID = 'namecheap-lock'

# TODO: Deal with stale locks
class NamecheapLock():
    def __init__(self):
        self.lockfile = lockfile.FileLock(os.path.join(tempfile.gettempdir(), u'namecheap'))

    def acquire(self, timeout=None):
        self.lockfile.acquire(timeout)

    def release(self):
        self.lockfile.release()

class MozAPILock(NamecheapLock):
    def __init__(self):
        self.lockfile = lockfile.FileLock(os.path.join(tempfile.gettempdir(), u'mozapi'))

def get_task_list():
    i = app.control.inspect()
    actives = i.active()
    al = []
    if actives is not None:
        for tasks in actives.values():
            al += tasks
    print u'Active (%d) %s: ' % (len(al), str(al))
    scheduled = i.scheduled()
    sl = []
    if scheduled is not None:
        for tasks in scheduled.values():
            sl += tasks
    print u'Scheduled (%d) %s' % (len(sl), str(sl))
    reserved = i.reserved()
    rl = []
    if reserved is not None:
        for tasks in reserved.values():
            rl += tasks
    print u'Reserved (%s) %s: ' % (len(rl), str(rl))
    at = al + sl + rl
    print u'Full list (%d): %s' % (len(at), str(at))
    return at

def is_project_task_active(project, task_list):
    pts = ProjectTask.objects.filter(project_id=project.id)
    task_list_ids = [t['id'] for t in task_list]
    for pt in pts:
        if pt.celery_id in task_list_ids:
            print u'Task found for project %d' % project.id
            return True
    print u'Unable to find tasks for project %d.' % project.id
    return False

@app.task(ignore_result=True)
def update_domain_metrics():
    lock = MozAPILock()
    try:
        lock.acquire(0)
    except lockfile.AlreadyLocked:
        # update already in progress, ignore
        return

    try:
        # find all domains in need of updating        
        checkables = set()
        for pd in ProjectDomain.objects.filter(state__in=['available'], url_metrics=None):
            try:
                m = URLMetrics.objects.get(query_url=pd.domain)
                if m.is_uptodate():
                    pd.url_metrics_id = m.id
                    pd.save()
                else:
                    checkables.add(pd.domain)
            except URLMetrics.DoesNotExist:
                checkables.add(pd.domain)
        print 'Total number of domains to check: %d' % len(checkables)
        # Gather login details
        # Set columns to gather (currently all 'free' columns)
        bf = URLMetrics.create_cols_bitflag([
            'Title',
            'Canonical URL',
            'External Links',
            'Links',
            'MozRank 10', 
            'MozRank Raw',
            'Subdomain MozRank 10',
            'Subdomain MozRank Raw',
            'HTTP Status Code',
            'Page Authority',
            'Domain Authority'])
        # use MozAPI to update them
        wait_time = AdminSetting.get_moz_api_wait_time()
        limit = int((60.0*60/wait_time)*0.9)

        for i, c in enumerate(checkables):
            print i, c
            params = AdminSetting.get_moz_params()
            params.append(('Cols', bf))
            r = requests.get(AdminSetting.get_moz_api_url()+'url-metrics/'+c, params=params)
            print r.url
            print r.status_code
            rtext = r.text
            print rtext
            if r.status_code == 200:
                rd = json.loads(rtext)
                try:
                    mm = URLMetrics.objects.get(query_url=c)
                except:
                    mm = URLMetrics()
                    mm.query_url = c
                mm.store_result(rd)
                mm.last_updated = timezone.now()
                mm.save()
                for pd in ProjectDomain.objects.filter(domain=c):
                    pd.url_metrics = mm
                    pd.save()
                for mp in UserProject.objects.filter(state='measuring'):
                    mp.update_state()
            r.close()
            print 'Done with %s, waiting...' % c
            time.sleep(wait_time)
            if i >= limit:
                break
    except Exception as e:
        lock.release()
        raise

    lock.release()

@app.task(ignore_result=True)
def check_project_tasks():
    projects = UserProject.objects.all()
    tl = get_task_list()
    for project in projects:
        if not project.state in [u'completed', u'error', u'paused'] and not is_project_task_active(project, tl):
            async_result = check_project_domains.delay(project.id)
            task_id = async_result.id
            print task_id
            project_task = ProjectTask()
            project_task.project_id = project.id
            project_task.celery_id = task_id
            project_task.type = u'checker'
            project_task.save()

            print u'Restarted task for project %d (task id: %s)' % (project.id, task_id)

@app.task(ignore_result=True)
def update_tlds():
    params = AdminSetting.get_api_params()
    params.append((u'Command', u'namecheap.domains.gettldlist'))
    r = requests.get(AdminSetting.get_api_url(), params=params)

    rtext = r.text
    print rtext

    # send_mail('Domain Checker - Project "%s" complete' % (pfile.filename), messagebody, reply_address, [user.email])
    send_mail(u'Domain Checker - TLD Update', u'The following response was received from the TLD update (using %s):\n\n%s' % (AdminSetting.get_api_url(), rtext), AdminSetting.get_value(u'noreply_address'), [AdminSetting.get_value(u'admin_address')])

    parser = etree.XMLParser(encoding=u'utf-8')
    rtree = etree.fromstring(rtext, parser=parser)
    rels = rtree.findall(u'./{http://api.namecheap.com/xml.response}CommandResponse/{http://api.namecheap.com/xml.response}Tlds/{http://api.namecheap.com/xml.response}Tld')

    rels = dict([(r.attrib[u'Name'], r) for r in rels])
    tlds = TLD.objects.all()
    with transaction.atomic():
        for tld in tlds:
            if tld.domain in rels.keys():
                rel = rels[tld.domain]
                tld.is_recognized = True
                tld.is_api_registerable = (rel.attrib[u'IsApiRegisterable'] == u'true')
                tld.description = rel.text
                tld.type = rel.attrib[u'Type']
            else:
                tld.is_recognized = False
                tld.is_api_registrable = False
                tld.type = u'unknown'
                tld.description = None
            tld.save()

        for ncd, rel in rels.items():
            if len(TLD.objects.filter(domain=ncd)) == 0:
                new_tld = TLD(domain=ncd, is_recognized=True, is_api_registerable=(rel.attrib['IsApiRegisterable'] == True), description=rel.text, type=rel.attrib['Type'])
                new_tld.save()
                print u'New TLD added: %s' % ncd

    print u'Finished processing tlds.'

def parse_namecheap_result(rstring):
    print rstring
    parser = etree.XMLParser(encoding='utf-8', recover=True)
    tree = etree.fromstring(rstring, parser=parser)
    check_raw = tree.findall(u'./{http://api.namecheap.com/xml.response}CommandResponse/{http://api.namecheap.com/xml.response}DomainCheckResult')
    error_raw = tree.findall(u'./{http://api.namecheap.com/xml.response}Errors/{http://api.namecheap.com/xml.response}Error')

    domain_results = []
    for check in check_raw:
        domain_results.append({
            u'domain' : check.attrib[u'Domain'],
            u'available' : (check.attrib[u'Available'] == 'true'),
            u'errorno' : int(check.attrib[u'ErrorNo']),
            u'description' : check.attrib[u'Description']})

    for result in domain_results:
        print result

    error_results = []
    for error in error_raw:
        error_results.append({
            u'number' : error.attrib[u'Number'],
            u'description' : error.text.strip()})

    return (domain_results, error_results)

@app.task(ignore_result=True)
def check_moz_update():
    if settings.DEBUG:
        logging.basicConfig() 
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger(u'requests.packages.urllib3')
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
    params = AdminSetting.get_moz_params()
    r = requests.get(AdminSetting.get_moz_api_url()+'metadata/last_update.json', params=params)
    status = r.status_code
    print status
    if status == 200:
        rtext = r.text
        print rtext
        rd = json.loads(rtext)
        mu = MozLastUpdate()
        mu.datetime = timezone.make_aware(datetime.datetime.fromtimestamp(int(rd['last_update'])), timezone.get_current_timezone())
        mu.retrieved = timezone.now()
        mu.save()
    r.close()


@app.task(ignore_result=True)
def check_project_domains(project_id):
    lock = NamecheapLock()
    project = UserProject.objects.get(id=project_id)
    if settings.DEBUG:
        logging.basicConfig() 
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger(u'requests.packages.urllib3')
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
    while True:
        lock.acquire()
        try:
            domain_list = project.projectdomain_set.filter(is_checked=False)[:AdminSetting.get_api_urls_per_request()]
            if len(domain_list) == 0:
                # project.state = u'completed'
                project.update_state(save=False)
                project.updated = timezone.now()
                project.completed_datetime = timezone.now()
                project.save()

                if project.state == 'completed':
                    pfile = UploadedFile.objects.get(project_id=project.id)
                    reply_address = AdminSetting.get_value(u'noreply_address')
                    server_address = AdminSetting.get_value(u'server_address')
                    messagebody = (u'The project "%s" has successfully completed.  You can view the results at the following address:\n\n' + \
                                  u'%s/project?id=%d\n\n' + \
                                  u'Thank you for using Domain Checker.') % (pfile.filename, server_address, project.id)
                    user = User.objects.get(id=project.user_id)
                    send_mail(u'Domain Checker - Project "%s" complete' % (pfile.filename), messagebody, reply_address, [user.email])
                lock.release()
                break

            domains = dict([(d.domain, d) for d in domain_list])
            domain_str = u','.join(domains.keys())

            params = AdminSetting.get_api_params()
            params.append((u'Command', u'namecheap.domains.check'))
            params.append((u'DomainList', domain_str))

            print u'Domains that willbe checked: %s' % domain_str
            print params
            r = requests.get(AdminSetting.get_api_url(), params=params)
            # print r.url
            # print r.headers
            sc = r.status_code
            print u'Status code: %d' % sc

            if sc == 200:
                rxml = r.text.encode(u'utf-8')
                (domain_results, error_results) = parse_namecheap_result(rxml)
                if len(domain_results) == 0 and len(error_results) > 0:
                    for er in error_results:
                        if int(er[u'number']) == 2030280:
                            # TLD not found - assume same result for all
                            for domain, d in domains.items():
                                d.state = u'error'
                                d.error = u'API unable to parse TLD for this domain (possible encoding issue)'
                                d.is_checked = True
                                d.last_checked = timezone.now()
                                d.save()
                            break
                        else:
                            # Assume catastrophic error
                            error_str = u'the API backend returned the following unrecoverable error(s):\n\n'
                            error_str += u'\n'.join([u'  %d: [%s] %s' % (i+1, er[u'number'], er[u'description']) for i, er in enumerate(error_results)])
                            raise Exception(error_str)

                for dr in domain_results:
                    print u'Finding match for "%s"...' % (dr[u'domain'])
                    for key in domains.keys():
                        # We use endswith to handle mailto: addresses, TODO: These should be handled at the parsing stage
                        if key.endswith(dr[u'domain']):
                            d = domains[key]
                            if dr[u'errorno'] != 0:
                                d.state = u'error'
                                d.error = u'API error (%d): %s' % (dr[u'errorno'], dr[u'description'])
                                print dr
                            else:
                                d.state = u'available' if dr[u'available'] else u'unavailable'
                                d.description = None
                            d.is_checked = True
                            d.last_checked = timezone.now()
                            d.save()
                            break

                for domain, d in domains.items():
                    if d.state == u'unchecked':
                        print u'Domain result not found (will recheck later): %s' % domain
            else:
                print u'Warning: Unexpected response while calling API code: %d, will retry after delay' % sc

            time.sleep(AdminSetting.get_api_wait_time())
            lock.release()
        except Exception as e:
            lock.release()
            project.state = u'error'
            project.error = u'Error occurred while checking domains - %s' % str(e).encode('utf-8')
            project.updated = timezone.now()
            project.completed_datetime = timezone.now()
            project.save()
            reply_address = AdminSetting.get_value(u'noreply_address')
            server_address = AdminSetting.get_value(u'server_address')
            messagebody = (u'The project "%s" has encountered an error:\n\n' + \
                  u'%s\n\nYou can view the results at the following address:\n\n' + \
                  u'%s/project?id=%d\n\n' + \
                  u'Thank you for using Domain Checker.') % \
                  (project.name(), project.error, server_address, project.id)
            user = User.objects.get(id=project.user_id)
            send_mail(u'Domain Checker - Project "%s" Error' % (project.name(),), messagebody, reply_address, [user.email])

            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            admin_email = AdminSetting.get_value(u'admin_address')
            admin_messagebody = (u'The user "%s" has encountered an unrecoverable error for project id %d.\n\n%s') % \
                (user.username, project.id, '\n'.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
            print admin_email
            print admin_messagebody
                
            send_mail(u'Domain Checker - User Unrecoverable Error', admin_messagebody, reply_address, [admin_email])

            # Propagate error to Celery handler
            raise


