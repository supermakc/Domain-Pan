"""
Domain checker views for the main module.

.. moduleauthor:: Chris Davoren <cdavoren@gmail.com>
"""
from __future__ import absolute_import
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.core.cache import cache
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from main.forms import URLFileForm
from main.models import TLD, ExcludedDomain, UserProject, UploadedFile, ProjectDomain, PreservedDomain, ProjectTask, AdminSetting, ExtensionPrefix, ProjectMetrics
from main.tasks import check_project_domains, update_tlds, update_metrics

import os, logging, re, json, string, random
from urlparse import urlparse
from domain_checker.celery import app

logger = logging.getLogger(__name__)
"""Logger name for the view module"""
schemecheck_re = re.compile(r'[^\.]*?//')
"""Regular expression for checking whether a scheme has been specified for a URL"""
iponly_re = re.compile(r'[^\.]*?//([0-9]{1,3}\.){3}[0-9]{1,3}[/$]')
"""Regular expression for checking whether a URL is an IP (not a domain name)"""
portend_re = re.compile(r'(.*?):[0-9]+$')
"""Regular expression for checking if there is a port number in a URL"""

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
    logger.debug('Active (%d) %s: ' % (len(al), str(al)))
    scheduled = i.scheduled()
    sl = []
    if scheduled is not None:
        for tasks in scheduled.values():
            sl += tasks
    logger.debug('Scheduled (%d) %s' % (len(sl), str(sl)))
    reserved = i.reserved()
    rl = []
    if reserved is not None:
        for tasks in reserved.values():
            rl += tasks
    logger.debug('Reserved (%s) %s: ' % (len(rl), str(rl)))
    at = al + sl + rl
    logger.debug('Full list (%d): %s' % (len(at), str(at)))
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
            logger.debug('Task found for project %d' % project.id)
            return True
    logger.debug('Unable to find tasks for project %d.' % project.id)
    return False
        
def load_tlds():
    """
    Returns the stored list of recognized top-level domains.
    """
    return [unicode(tld.domain) for tld in TLD.objects.all().order_by('-is_recognized','-is_api_registerable')]

def load_exclusions():
    """
    Returns the stored list of domains that should be excluded from availability checking.
    """
    return [unicode(exclusion.domain) for exclusion in ExcludedDomain.objects.all()]

def load_preservations():
    """
    Returns the stored list of domains for which subdomains should be preserved.
    """
    return [unicode(preservation.domain) for preservation in PreservedDomain.objects.all()]

def deep_delete_project(project):
    """
    Removes a project from the system, including its uploaded file, domains and metrics associations.

    Args:
      project (UserProject): The project to delete.
    """
    try:
        uploaded_file = UploadedFile.objects.get(project_id=project.id)
        uploaded_file.delete()
    except UploadedFile.DoesNotExist:
        pass
    
    project_domains = ProjectDomain.objects.filter(project_id=project.id)
    for pd in project_domains:
        pd.delete()

    for pm in ProjectMetrics.objects.filter(project=project):
        pm.delete()

    project.delete()

def remove_subdomains(url, tlds):
    """
    Takes a given URL and returns the corresponding top-level domain.  Note that this code has been adapted from an answer on StackOverflow.

    Args:
      url (str): The url to find the TLD for.
      tlds (list): A list of recognized TLD's.

    Raises:
      ValueError: If the TLD of the URL is not recognized.
    """
    # Checks for presence of // before domain (required by urlparse).  If it does not exist, add it.
    if schemecheck_re.match(url) == None:
        url = u'//'+url

    # Use URL to retrieve the full domain name (including subdomains)
    full_domain = urlparse(url, scheme='http')[1]

    # Split the parsed domain into elements to recognise the portion that represents the TLD
    url_elements = full_domain.split('.')
    if len(url_elements) > 0:
        pe = portend_re.match(url_elements[-1])
        if pe is not None:
            url_elements[-1] = pe.group(1)
    for i in range(-len(url_elements), 0):
        last_i_elements = url_elements[i:]
        #    i=-3: ["abcde","co","uk"]
        #    i=-2: ["co","uk"]
        #    i=-1: ["uk"] etc

        candidate = u".".join(last_i_elements) # abcde.co.uk, co.uk, uk
        wildcard_candidate = u".".join(["*"] + last_i_elements[1:]) # *.co.uk, *.uk, *
        exception_candidate = u"!" + candidate

        # match
        if (exception_candidate in tlds):
            return (exception_candidate, u".".join(url_elements[i:]), full_domain) 
        elif (candidate in tlds):
            return (candidate, u".".join(url_elements[i-1:]), full_domain)
        """
        # The wildcard format plays havoc with the way NameCheap TLDs are processed, so we skip this
        elif (wildcard_candidate in tlds):
            return (wildcard_candidate, ".".join(url_elements[i-1:]), full_domain)
        """

    # The TLD of this URL is not recognised
    logger.debug(url_elements)
    raise ValueError(u"Invalid address or domain not in recognized list of TLDs")

def extract_domains(file_content, fail_email, filename):
    """
    Takes the contents of an uploaded file and returns a series a tuple of results representing parsed domains of different types.  If any lines in the file cannot be parsed, an email notification is sent to the given address with details.

    Args:
      file_content (str): The raw content of the file.
      fail_email (str): Email address of user to notify if there is a fatal error
      filename (str): The original filename

    Returns:
      A tuple containing three items:
         1.  Correctly parsed domains
         2.  Domains that failed, are unrecognized or unregisterable
         3.  A list of lines in the file that could not be parsed
    """
    tlds = load_tlds()
    exclusions = load_exclusions()
    preservations = load_preservations()
    domain_list = set()
    ln = 0
    failed_lines = []
    failed_domains = []
    failed_set = set()
    for url in file_content.split('\n'):
        ln += 1
        logger.debug(type(url))
        # url = url.decode('utf-8')
        # url = unicode(url, errors='ignore')
        if len(url) == 0 or url[0] in '/\n':
            continue
        # logger.debug(url.strip())
        try:
            url = url.strip()
            if iponly_re.match(url) is not None:
                raise ValueError(u'IP only - no domain to extract')
            elif url.startswith('javascript:'):
                raise ValueError(u'Javascript hook')
            (tld_match, domain, full_domain) = remove_subdomains(url.strip(), tlds)
            tld = TLD.objects.get(domain=tld_match)
            if domain in failed_set:
                continue
            if not tld.is_recognized:
                failed_domains.append((domain, u'unregisterable', u'Unregisterable TLD (%s)' % tld_match))
                failed_set.add(domain)
            elif not tld.is_api_registerable:
                failed_domains.append((domain, u'unregisterable', u'TLD recognized but cannot be registered through the API (%s)'% tld_match))
                failed_set.add(domain)
            elif domain in exclusions:
                failed_domains.append((domain, u'unregisterable', u'Domain explicitly excluded (%s)' % domain))
                failed_set.add(domain)
            elif domain in preservations:
                failed_domains.append((full_domain, u'special', u'Domain is reserved for special processing (%s)' % domain))
                failed_set.add(full_domain)
            else:
                domain_list.add(domain)
        except ValueError as e:
            failed_lines.append((ln, url.strip(), str(e)))

    if len(failed_lines) > 0:
        error_email = u'The following domains failed while reading the file "%s":\n\n' % filename.encode('utf-8')
        for fd in failed_lines:
            error_email += u'Line %d: %s (%s)\n' % (fd[0], 
                fd[1],
                fd[2])
        logger.debug(error_email)
        send_mail(u'Domain Checker: Failed Domains', error_email, AdminSetting.get_value('noreply_address'), [fail_email])
    return (domain_list, failed_domains, failed_lines)

def index(request):
    """
    View: The root page.
    """
    return render(request, 'main/index.html', {'allow_new_registrations' : AdminSetting.get_value('allow_new_registrations'),})

# TODO: Should properly use CSRF tokens for this (currently implemented as AJAX which makes that awkward - see Django documentation)
@csrf_exempt
def check_login(request):
    """
    AJAX target: Check the given username and password for validation.  Uses the Django authentication system to authenticate the user and returns a JSON success result.
    """
    result = {'result' : 'failure'}
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        logger.debug('Login attempt, username: "%s", password: "%s"' % (username, password))
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                result['result'] = 'success'
    return HttpResponse(json.dumps(result))

def logout_user(request):
    """
    View: Logs out the currently authenticated user.  Redirects to the index page.
    """
    if request.user.is_authenticated():
        logout(request)
    return redirect('index')

@login_required(login_url='/')
def profile(request):
    """
    View:  Profile page for an authenticated user.  Redirects to index page if unauthenticated.
    """
    if not request.user.is_authenticated():
        return redirect('index')
    # Check session variable for pending messages
    profile_message = None
    profile_messagetype = None
    if request.session.has_key('profile_message'):
        profile_message = request.session['profile_message']
        profile_messagetype = request.session['profile_messagetype']
        # Clear messages once displayed
        del request.session['profile_message']
        del request.session['profile_messagetype']

    return render(request, 
        'main/profile.html', 
        {
            'user' : request.user, 
            'profile_message' : profile_message, 
            'profile_messagetype' : profile_messagetype,})

@login_required(login_url='/')
def project_list(request):
    """
    View:  Project list for an authenticated user.  Redirects to index page if unauthenticated.
    """
    if not request.user.is_authenticated():
        return redirect('index')
    profile_message = None
    profile_messagetype = None
    if request.session.has_key('profile_message'):
        profile_message = request.session['profile_message']
        profile_messagetype = request.session['profile_messagetype']
        del request.session['profile_message']
        del request.session['profile_messagetype']
    uploadform = URLFileForm(request.POST, request.FILES)
    projects = UserProject.objects.filter(user_id=request.user.id).order_by('-created')
    for project in projects:
        try:
            project.file = UploadedFile.objects.get(project_id=project.id)
            logger.debug('Filename: %s' % project.file.filename)
        except UploadedFile.DoesNotExist:
            pass
        project.domains = ProjectDomain.objects.filter(project_id=project.id)
    return render(
        request,
        'main/project_list.html',
        {
            'user' : request.user,
            'projects' : projects,
            'uploadform' : uploadform, 
            'profile_message' : profile_message,
            'profile_messagetype' : profile_messagetype,})

@login_required(login_url='/')
def upload_project(request):
    """
    View:  Processes new project file upload of an authenticated user.  Redirects to index page if unauthenticated.  Otherwise once the file is parsed for domains to process, the user is redirected back to their project listing with an appropriate success or failure message.
    """
    if not request.user.is_authenticated():
        logger.debug('Unauthenticated user.')
        return redirect('index')
    project = None
    if request.method == 'POST':
        uploadform = URLFileForm(request.POST, request.FILES)
        logger.debug('Attempting to upload project...')
        if uploadform.is_valid():
            logger.debug('Form is valid.')
            file_contents = unicode(request.FILES['file'].read(), errors='ignore')
            (domain_list, failed_domains, failed_lines) = extract_domains(file_contents, request.user.email, request.FILES['file'].name)
            projectdomains = []
            with transaction.atomic():
                project = UserProject(state='checking', last_updated=timezone.now(), user_id=request.user.id)
                parse_error_str = ''
                # If any lines failed, track them
                if len(failed_lines) > 0:
                    for fd in failed_lines:
                        parse_error_str += '%d: %s (%s)\n' % (fd[0], fd[1], fd[2])
                    project.parse_errors = parse_error_str
                project.save()

                # Store uploaded file in database
                projectfile = UploadedFile(filename=request.FILES['file'].name, filedata=file_contents, project_id=project.id)

                # Create and associate project domain records
                for domain in domain_list:
                    projectdomains.append(ProjectDomain(domain=domain, subdomains_preserved=False, is_checked=False, state='unchecked', last_checked=timezone.now(), project_id=project.id))
                for (domain, state, error) in failed_domains:
                    projectdomains.append(ProjectDomain(domain=domain, subdomains_preserved=False, is_checked=True, state=state, last_checked=timezone.now(), project_id=project.id, error=error))
                projectfile.save()
                [pd.save() for pd in projectdomains]

            # Initial celery task to check availability of parsed domains
            if project.projectdomain_set.exclude(state='error').count() == 0:
                project.state = 'completed'
                project.save()
                request.session['profile_message'] = 'Project "%s" successfully uploaded but no valid domains were found for checking.' % request.FILES['file'].name
                request.session['profile_messagetype'] = 'warning'
            else:
                task_id = check_project_domains.delay(project.id)

                project_task = ProjectTask()
                project_task.project_id = project.id
                project_task.celery_id = task_id
                project_task.type = 'checker'
                project_task.save()

                request.session['profile_message'] = 'Project "%s" successfully uploaded.  You will be emailed when domain checking is complete.' % request.FILES['file'].name
                request.session['profile_messagetype'] = 'success'

                return redirect('project_list')
        else:
            # If an error occurred, inform the user
            logger.debug(uploadform.errors)
            request.session['profile_message'] = '<b>Project not uploaded.</b> The following errors occurred: %s' % uploadform.errors
            request.session['profile_messagetype'] = 'danger'
            return redirect('project_list')

@login_required(login_url='/')
def change_details(request):
    """
    View:  Processes change of personal details for an authenticated user.  Redirects to index page if not authenticated.  Otherwise once the update is complete, the user is redirected back to the their profile page.
    """
    if not request.user.is_authenticated():
        return redirect('index')
    first_name = request.GET['first_name']
    last_name = request.GET['last_name']
    request.user.first_name = first_name
    request.user.last_name = last_name
    request.user.save()
    request.session['profile_message'] = 'Your details have been successfully updated'
    request.session['profile_messagetype'] = 'success'
    return redirect('profile')

@login_required(login_url='/')
def change_email(request):
    """
    View:  Processes change of email for an authenticated user.  Redirects to index page if not authenticated.  Otherwise once the update is complete, the user is redirected back to the their profile page.
    """
    if not request.user.is_authenticated():
        return redirect('index')
    email = request.GET['email1']
    request.user.email = email
    request.user.save()
    request.session['profile_message'] = 'Your email has been successfully updated'
    request.session['profile_messagetype'] = 'success'
    return redirect('profile')

@login_required(login_url='/')
def change_password(request):
    """
    View:  Processes change of password for an authenticated user.  Redirects to index page if not authenticated.  Otherwise once the update is complete, the user is redirected back to the their profile page.
    """
    if not request.user.is_authenticated():
        return redirect('index')
    if not request.method == 'GET':
        return redirect('profile')
    oldpassword = request.GET['oldpassword']
    newpassword = request.GET['newpassword1']
    user = authenticate(username=request.user.username, password=oldpassword)
    if user is not None:
        user.set_password(newpassword)
        user.save()
        request.session['profile_message'] = 'Password successfully changed.'
        request.session['profile_messagetype'] = 'success'
    else:
        request.session['profile_message'] = 'Password unchanged: the entered old password is invalid.'
        request.session['profile_messagetype'] = 'danger'
    return redirect('profile')

@login_required(login_url='/')
def delete_project(request):
    """
    View:  Deletes a specified project for an authenticated user.  Redirects to index page if not authenticated.  Otherwise, a deep delete of the given project is performed and the user is redirected back to their project listing page with an appropriate message.
    """
    if not request.user.is_authenticated():
        return redirect('index')
    pid = int(request.GET['pid'])
    project = UserProject.objects.get(id=pid)
    if project.user_id != request.user.id:
        return redirect('index')
    try:
        pname = UploadedFile.objects.get(project_id=project.id).filename
    except UploadedFile.DoesNotExist:
        pname = str(project.id)
    with transaction.atomic():
        deep_delete_project(project)
    request.session['profile_message'] = 'Project "%s" has been deleted.' % pname
    request.session['profile_messagetype'] = 'success'
    return redirect('project_list')

@transaction.atomic
@login_required(login_url='/')
def update_admin(request):
    """
    View:  Updates administration settings for an authenticated administrator or staff member.  User is redirected back to administration panel once complete.
    """
    if not request.user.is_authenticated() or not request.user.is_staff or request.method != 'POST':
        return redirect('index')
    exclusions = request.POST['exclusions']
    preserved = request.POST['preserved']

    # Clear old exclusion/preserved/extension domains (will be parsed from scratch)
    ExcludedDomain.objects.all().delete()
    PreservedDomain.objects.all().delete()

    # Parse text area of exclusion domains (one on each line)
    for e in exclusions.split('\n'):
        e = e.strip()
        if len(e) == 0:
            continue
        ed = ExcludedDomain(domain=e)
        ed.save()

    # Parse text area of preservation domains (one on each line)
    for p in preserved.split('\n'):
        p = p.strip()
        if len(p) == 0:
            continue
        pd = PreservedDomain(domain=p)
        pd.save()

    # Only update central administration settings if the user is recorded as an administrator (not just staff)
    if request.user.is_superuser:

        # Clear old extension prefixes
        extensions = request.POST['extensions']
        ExtensionPrefix.objects.all().delete()

        # Parse text area of extension prefixes (one on each line)
        for x in extensions.split('\n'):
            x = x.strip()
            if len(x) == 0:
                continue
            ep = ExtensionPrefix(prefix=x)
            ep.save()

        # Note that the field names are used to determine the AdminSetting key
        ads = AdminSetting.objects.all()

        for ad in ads:
            if ad.type == 'boolean':
                ad.value = 'true' if request.POST.has_key(ad.key) else 'false'
                ad.save()
            elif request.POST.has_key(ad.key):
                if len(request.POST[ad.key]) == 0:
                    request.session['profile_message'] = '<b>Error updating settings:</b> Field "%s" cannot be blank' % ad.key
                    request.session['profile_messagetype'] = 'error'
                    return redirect('admin_settings')
                else:
                    ad.value = request.POST[ad.key]
                    ad.save()

        staff = request.POST['staff']
        staff_list = []
        for s in staff.split('\n'):
            s = s.strip()
            if len(s) == 0:
                continue
            staff_list.append(s)
            
        for u in User.objects.all():
            u.is_staff = u.username in staff_list
            u.save()

    request.session['profile_message'] = 'Administration settings successfully updated'
    request.session['profile_messagetype'] = 'success'
    return redirect('admin_settings')

def register_user(request):
    """
    View:  Registers a new user.  If registrations are disabled, the user is redirected back to the index page.  Otherwise a new user is created and authenticated, and the user is then redirected to their new profile page.
    """
    if not AdminSetting.get_value('allow_new_registrations'):
        return redirect('index')

    if request.method != 'POST':
        return redirect('index')

    username = request.POST['username']
    first_name = request.POST['first_name']
    last_name = request.POST['last_name']
    email = request.POST['email']
    password = request.POST['password']

    user = User.objects.create_user(username, email, password, first_name=first_name, last_name=last_name)
    user.save()

    user = authenticate(username=username, password=password)
    login(request, user)

    return redirect('profile')

@csrf_exempt
def check_username(request):
    """
    AJAX target:  Checks if a given username is available and returns the JSON 'available':True if so.
    """
    result = {'available':False}
    if request.method == 'POST':
        username = request.POST['username']
        if len(User.objects.filter(username=username)) == 0:
            result['available'] = True;
    return HttpResponse(json.dumps(result))

@csrf_exempt
def reset_user(request):
    result = {'result':'error', 'message':'No user exists with that email.'}
    if request.method != 'POST':
        return redirect('index')

    email = request.POST['email']
    user = User.objects.filter(email=email)
    if len(user) == 0:
        return HttpResponse(json.dumps(result))
    else:
        user = user[0]

    return_address = 'noreply@dc.charlery.me'
    
    if request.POST['reset'] == 'username':
        send_mail('Domain Checker: Username retrieval', 'Your username is "%s"' % user.username, return_address, [email])
        result['result'] = 'success'
        result['message'] = 'Your username has been sent to "%s"' % email
    elif request.POST['reset'] == 'password':
        chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
        newpassword = ''.join(random.choice(chars) for x in range(10))
        user.set_password(newpassword)
        user.save()
        send_mail('Domain Checker: Password reset', 'You have been granted a temporary password of "%s".  Please change it as soon as possible.' % newpassword, return_address, [email])
        result['result'] = 'success'
        result['message'] = 'A new password has been sent to "%s"' % email

    return HttpResponse(json.dumps(result))

@login_required(login_url='/')
def project(request):
    """
    View:  Lists details of a specific project for an authenticated user, including domains, metrics, errors and other messages.
    """
    if not request.user.is_authenticated() or request.method != 'GET':
        return redirect('index')
    
    try:
        project = UserProject.objects.get(id=request.GET['id'])
        # Does the user actually own this project?  If not, redirect back to profile
        if project is None or project.user_id != request.user.id:
            request.session['profile_message'] = 'The specified project does not exist or belongs to another user.'
            request.session['profile_messagetype'] = 'danger'
            return redirect('project_list')

        project_file = UploadedFile.objects.get(project_id=project.id)

        project_domains = project.projectdomain_set.all().order_by('-is_checked', 'state', 'domain')
        checkable_domains = project_domains.exclude(state__in=['error', 'unregisterable', 'special'])
        completed_domains = project_domains.filter(is_checked=True)
        unregisterable_domains = completed_domains.filter(state='unregisterable')
        special_domains = project_domains.filter(state='special')
        error_domains = project_domains.filter(state='error')

        return render(
            request, 
            'main/project.html', {
                'project' : project, 
                'project_file' : project_file, 
                'domains' : checkable_domains, 
                'errors' : error_domains, 
                'unregisterables' : unregisterable_domains, 
                'specials' : special_domains, 
                'project_error_formatted' : None if project.error is None else project.error.replace('\n', '<br />') 
        })
    except UserProject.DoesNotExist as e:
        request.session['profile_message'] = 'The specified project does not exist or belongs to another user.'
        request.session['profile_messagetype'] = 'danger'
        return redirect('profile')

@login_required(login_url='/')
def manual_update_tlds(request):
    """
    View:  Manually initiates a new Celery task that calls the Namecheap API to update the list of recognized top-level domains.  Redirects the user back to the administration panel.
    """
    if not request.user.is_authenticated() or not request.user.is_superuser:
        return redirect('index')

    update_tlds.delay()
    request.session['profile_message'] = 'Top level domain information is being synchronized from NameCheap.'
    request.session['profile_messagetype'] = 'success'

    return redirect('admin_settings')

def manual_update_metrics(request):
    """
    View:  Initiates a Celery task to check and update metrics for all projects.  Redirects the user back to the administration panel.
    """
    if not request.user.is_authenticated() or not request.user.is_superuser:
        return redirect('index')

    update_metrics.delay()
    request.session['profile_message'] = 'Manual URL metrics update initiated.'
    request.session['profile_messagetype'] = 'success'

    return redirect('admin_settings')

def manual_update_states(request):
    """
    View:  Manually updates the state of all projects in the database.  Redirects the user back to the administration panel.
    """
    if not request.user.is_authenticated() or not request.user.is_superuser:
        return redirect('index')

    for p in UserProject.objects.all():
        p.update_state()
        logger.debug(p.name)
        logger.debug('  Measurable domains: %d' % len(p.get_measurable_domains()))
        logger.debug('  Measured domains: %d' % len(p.get_measured_domains()))

    request.session['profile_message'] = 'Manual project state update complete.'
    request.session['profile_messagetype'] = 'success'

    return redirect('admin_settings')

@login_required(login_url='/')
def admin_settings(request):
    """
    View:  The administration panel (available to staff and superusers only - otherwise the user is redirected back to their profile page).  Note that global administration settings are available to superusers only.
    """
    if not request.user.is_authenticated():
        return redirect('index')

    if not request.user.is_staff:
        return redirect('profile')

    profile_message = None
    profile_messagetype = None
    if request.session.has_key('profile_message'):
        profile_message = request.session['profile_message']
        profile_messagetype = request.session['profile_messagetype']
        del request.session['profile_message']
        del request.session['profile_messagetype']

    staff = None
    admin = {}
    exclusions = '\n'.join([e.domain for e in ExcludedDomain.objects.all()])
    preserved = '\n'.join([p.domain for p in PreservedDomain.objects.all()])
    extensions = '\n'.join([x.prefix for x in ExtensionPrefix.objects.all()])
    for ads in AdminSetting.objects.all():
        admin[ads.key] = ads.value

    if request.user.is_superuser:
        staff = '\n'.join([u.username for u in User.objects.filter(is_staff=True)])

    return render(
        request, 
        'main/admin.html', 
        {
            'user' : request.user, 
            'profile_message' : profile_message, 
            'profile_messagetype' : profile_messagetype, 
            'exclusions' : exclusions, 
            'preserved' : preserved,
            'extensions' : extensions,
            'staff' : staff,
            'admin' : admin})
