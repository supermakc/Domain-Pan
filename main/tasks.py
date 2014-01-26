"""
Domain checker background tasks for the main module.

.. moduleauthor:: Chris Davoren <cdavoren@gmail.com>
"""

from __future__ import absolute_import
import sys, os, copy, time, logging, json, tempfile, sqlite3, traceback, datetime
from lxml import etree

from django.db import transaction
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.core.cache import cache

from domain_checker.celery import app
from main.models import ProjectDomain, UserProject, UploadedFile, TLD, AdminSetting, ProjectTask, URLMetrics, MozLastUpdate, ProjectMetrics

import requests, lockfile

class NamecheapLock():
    """
    Represents a lock on the Namecheap API ensuring mutually exclusive access for all processes.

    .. note:: Currently implemented as a file lock through the lockfile module.
    """
    def __init__(self):
        self.lockfile = lockfile.FileLock(os.path.join(tempfile.gettempdir(), u'namecheap'))

    def acquire(self, timeout=None):
        """
        Acquires the lock.

        Args:
          timeout (int): Time out for acquiring the lock in seconds.
        """
        self.lockfile.acquire(timeout)

    def release(self):
        """
        Releases the lock.
        """
        self.lockfile.release()

class MozAPILock(NamecheapLock):
    """
    Represents a lock on the Moz API ensuring mutually exclusive access for all processes.

    .. note:: Currently implemented as a file lock with the lockfile module.
    """
    def __init__(self):
        self.lockfile = lockfile.FileLock(os.path.join(tempfile.gettempdir(), u'mozapi'))

def get_task_list():
    """
    Returns a list of all currently registered Celery tasks (active, scheduled and reserved).
    """
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
    """
    Returns whether there are any tasks currently running for the given project.

    .. note:: Project tasks associations are not currently consistently implemented or used.
    """
    pts = ProjectTask.objects.filter(project_id=project.id)
    task_list_ids = [t['id'] for t in task_list]
    for pt in pts:
        if pt.celery_id in task_list_ids:
            print u'Task found for project %d' % project.id
            return True
    print u'Unable to find tasks for project %d.' % project.id
    return False

def check_moz_domain(m, cols, wait_time):
    """
    Calls the Moz API for the url of the given URLMetric.

    Args:
      m (URLMetrics): The metrics object whose query_url to use in the call.
      cols (list): A list of fields the call should return.  See the URLMetrics class for more details.
      wait_time (int): Number of seconds to wait before releasing the API lock after the call has returned.
    """
    lock = MozAPILock()
    lock.acquire()
    params = AdminSetting.get_moz_params()
    params.append(('Cols', cols))
    try:
        r = requests.get(AdminSetting.get_moz_api_url()+'url-metrics/'+m.query_url, params=params)
        rtext = r.text
        if r.status_code == 200:
            # Retrieve the JSON result
            rd = json.loads(rtext)
            # Store the fields in the URLMetrics object
            m.store_result(rd)
            # Update the status of the URLMetrics
            m.last_updated = timezone.now()
            m.save()
        r.close()
        print u'Done with %s, waiting (new)...' % m.query_url
        # Wait the specified time
        time.sleep(wait_time)
    except Exception as e:
        lock.release()
        raise
    lock.release()

def get_extensions(urlmetrics):
    """
    Returns a list of URLMetrics that represent extensions (i.e. addition of 'www.') to the given URLMetrics.
    """
    ex_prefixes = ['www.']
    extensions = []
    for ex in ex_prefixes:
        if urlmetrics.query_url.startswith(ex):
            # Skip if the given object already starts with the extension
            continue
        extension_url = ex+urlmetrics.query_url
        # Check if a URLMetrics object with the given extension already exists, otherwise create it
        try:
            exu = URLMetrics.objects.get(query_url=extension_url)
        except URLMetrics.DoesNotExist:
            exu = URLMetrics(query_url=extension_url)
        exu.extended_from = urlmetrics
        exu.save()
        extensions.append(exu)
    return extensions

def associate_project_metrics(project):
    """
    Checks to ensure that all the parsed domains of the given project are represented by a URLMetrics association.  A new URLMetrics object is created if an appropriate one does not exist.

    Args:
      project (UserProject): The project to check.
    """
    for pd in project.projectdomain_set:
        metric_associated = False
        for um in project.urlmetrics:
            if um.urlmetrics.query_url == pd.domain:
                metric_associated = True
                break
        if not metric_associated:
            newum = None
            try:
                newum = URLMetrics.objects.get(query_url=pd.domain)
            except URLMetrics.DoesNotExist:
                newum = URLMetrics(query_url=query_url.pd_domain)
                newum.save()
            pm = ProjectMetrics(project=project, urlmetrics=newum, is_checked=False, is_extension=False)
            pm.save()

@app.task(ignore_result=True)
def update_project_metrics(project_id):
    """
    Updates all the URLMetrics associated with the given project id through the Moz API.  If the MozRank of a URL is over the set threshold, extension URLs are created and also checked.

    Args:
      project_id (int): The ID of the project to update.
    """
    p = UserProject.objects.get(id=project_id)
    # Retrieve all fields available with free Moz API registration
    cols = URLMetrics.create_cols_bitflag([
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
    wait_time = AdminSetting.get_moz_api_wait_time()
    associate_project_metrics(p)
    pmetrics = ProjectMetrics.objects.filter(project=p, is_checked=False)
    for pm in pmetrics:
        with transaction.atomic():
            if not pm.urlmetrics.is_uptodate():
                check_moz_domain(pm.urlmetrics, cols, wait_time)
            if not pm.is_extension and pm.urlmetrics.mozrank_10 >= 1.0:
                extensions = get_extensions(pm.urlmetrics)
                print u'Getting extensions (%d)' % len(extensions)
                for ex in extensions:
                    print u'  %s' % ex.query_url
                    try:
                        newpm = ProjectMetrics.objects.get(project=p, urlmetrics=ex)
                    except ProjectMetrics.DoesNotExist:
                        newpm = ProjectMetrics(project=p, urlmetrics=ex, is_checked=True, is_extension=True)
                    if not ex.is_uptodate():
                        print u'  Checking extension: %s' % ex.query_url
                        check_moz_domain(ex, cols, wait_time)
                    else:
                        print u'  Extension already checked: %s' % ex.query_url
                    newpm.is_checked = True
                    newpm.save()
                
            pm.is_checked=True
            pm.save()
    p.update_state()
    p.save()

@app.task(ignore_result=True)
def update_metrics():
    """
    Updates URL metrics for all projects (if not up to date).  This is intended to be a regular check (via celerybeat).
    """
    with transaction.atomic():
        for p in UserProject.objects.all():
            if p.projectmetrics_set.filter(is_checked=False).count() > 0:
                update_project_metrics.delay(p.id)

@app.task(ignore_result=True)
def check_project_tasks():
    """
    Checks to see if any incomplete projects do not currently have any running celery tasks associated with them.  This can happen if e.g. the server is reset in the middle of a check.  If one is found, the check is restarted.  This is intended to be a regular check (via celerybeat).
    """
    projects = UserProject.objects.all()
    tl = get_task_list()
    for project in projects:
        if not project.state in [u'measuring', u'completed', u'error', u'paused'] and not is_project_task_active(project, tl):
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
    """
    Calls the Namecheap API to update the list of recognized and registerable top-level domains.  This is currently initiated manually via the administration panel.
    """
    params = AdminSetting.get_api_params()
    params.append((u'Command', u'namecheap.domains.gettldlist'))
    r = requests.get(AdminSetting.get_api_url(), params=params)
    rtext = r.text

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
    """
    Takes the raw XML result from a Namecheap API call and returns the results compiled in a more easily referenced dictionary form.  The LXML module is used to parse the XML.

    Args:
      rstring (str): The raw XML call result.
    """
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

    """
    for result in domain_results:
        print result
    """

    error_results = []
    for error in error_raw:
        error_results.append({
            u'number' : error.attrib[u'Number'],
            u'description' : error.text.strip()})

    return (domain_results, error_results)

@app.task(ignore_result=True)
def check_moz_update():
    """
    Calls the Moz API to determine when the Moz data was last updated.  This information is recorded and used to determine whether URLMetrics are still up to date.
    """
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
    """
    Use the Namecheap API to update availability status for all the domains associated with the given project.

    Args:
      project_id (int): The ID of the project to check domains for.
    """
    lock = NamecheapLock()
    project = UserProject.objects.get(id=project_id)
    # Enable debug output
    if settings.DEBUG:
        logging.basicConfig() 
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger(u'requests.packages.urllib3')
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
    while True:
        lock.acquire()
        try:
            # Retrieve list of unchecked domains (limited by the set limit of domains per call)
            domain_list = project.projectdomain_set.filter(is_checked=False)[:AdminSetting.get_api_urls_per_request()]
            # If no domains unchecked, progress project to the next stage (usually metrics measuring)
            if len(domain_list) == 0:
                project.update_state(save=False)
                project.save()

                lock.release()
                break

            # Fold the list into a dictionary for easy reference
            domains = dict([(d.domain, d) for d in domain_list])
            domain_str = u','.join(domains.keys())

            params = AdminSetting.get_api_params()
            params.append((u'Command', u'namecheap.domains.check'))
            params.append((u'DomainList', domain_str))

            print u'Domains that will be checked: %s' % domain_str
            print params

            # Make the call to the Namecheap API (retry 3 times then fail)
            retries = 0
            while True:
                try:
                    r = requests.get(AdminSetting.get_api_url(), params=params)
                    break
                except requests.exceptions.ConnectionError as ce:
                    retries += 1
                    if retries >= 3:
                        raise ce
                    time.sleep(5)

            sc = r.status_code
            print u'Status code: %d' % sc

            if sc == 200:
                rxml = r.text.encode(u'utf-8')
                (domain_results, error_results) = parse_namecheap_result(rxml)
                if len(domain_results) == 0 and len(error_results) > 0:
                    # Handle specific but rare Namecheap API errors gracefully
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
                        elif int(er[u'number']) == 3031510:
                            # Denied authorization for this domain
                            for domain, d in domains.items():
                                d.state = u'error'
                                d.error = u'API denies authorisation to check this domain (reason not given)'
                                d.is_checked = True
                                d.last_checked = timezone.now()
                                d.save()
                            break
                        else:
                            # Assume catastrophic error
                            error_str = u'the API backend returned the following unrecoverable error(s):\n\n'
                            error_str += u'\n'.join([u'  %d: [%s] %s' % (i+1, er[u'number'], er[u'description']) for i, er in enumerate(error_results)])
                            raise Exception(error_str)

                """
                Match the call results to the domain list and store them.  If appropriate, create and associate a metrics object for the project.
                """
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
                            if d.state == u'available':
                                try:
                                    um = URLMetrics.objects.get(query_url=d.domain)
                                except URLMetrics.DoesNotExist:
                                    um = URLMetrics(query_url=d.domain)
                                    um.save()
                                pm = ProjectMetrics(project=project, urlmetrics=um, is_checked=False, is_extension=False)
                                pm.save()
                            break

                # Make a debug note if a requested domain does not appear in the results (likely an error occurred)
                for domain, d in domains.items():
                    if d.state == u'unchecked':
                        print u'Domain result not found (will recheck later): %s' % domain
            else:
                print u'Warning: Unexpected response while calling API code: %d, will retry after delay' % sc

            r.close()
            time.sleep(AdminSetting.get_api_wait_time())
            lock.release()
        except Exception as e:
            lock.release()

            # A fatal error has occurred, set the project state appropriately and send an email to the user.
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

        project.update_state()
        # If any domains require metrics retrieval, start the appropriate background task
        if project.state == u'measuring':
            update_project_metrics.delay(project.id)


