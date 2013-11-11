# Create your views here.
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.core.cache import cache
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from forms import URLFileForm
from models import TLD, ExcludedDomain, UserProject, UploadedFile, ProjectDomain, PreservedDomain

import os, logging, re, json, string, random
from urlparse import urlparse

TLDS_CACHE_KEY = 'TDLS_CACHE_KEY'
EXCLUSION_CACHE_KEY = 'EXCLUSION_CACHE_KEY'

logger = logging.getLogger(__name__)
schemecheck_re = re.compile(r'[^\.]*?//')
iponly_re = re.compile(r'[^\.]*?//([0-9]{1,3}\.){3}[0-9]{1,3}[/$]')
portend_re = re.compile(r'(.*?):[0-9]+$')

def load_tlds():
    return [tld.domain for tld in TLD.objects.filter(included=True)]

def load_exclusions():
    return [exclusion.domain for exclusion in ExcludedDomain.objects.all()]

def deep_delete_project(project):
    uploaded_file = UploadedFile.objects.get(project_id=project.id)
    uploaded_file.delete()
    
    project_domains = ProjectDomain.objects.filter(project_id=project.id)
    for pd in project_domains:
        pd.delete()

    project.delete()

def remove_subdomains(url, tlds):
    # Checks for presence of // before domain (required by urlparse)
    if schemecheck_re.match(url) == None:
        url = '//'+url

    url_elements = urlparse(url, scheme='http')[1].split('.')
    if len(url_elements) > 0:
        pe = portend_re.match(url_elements[-1])
        if pe is not None:
            url_elements[-1] = pe.group(1)
    # logger.debug(urlparse(url).hostname)
    # url_elements = ["abcde","co","uk"]

    for i in range(-len(url_elements), 0):
        last_i_elements = url_elements[i:]
        #    i=-3: ["abcde","co","uk"]
        #    i=-2: ["co","uk"]
        #    i=-1: ["uk"] etc

        candidate = ".".join(last_i_elements) # abcde.co.uk, co.uk, uk
        wildcard_candidate = ".".join(["*"] + last_i_elements[1:]) # *.co.uk, *.uk, *
        exception_candidate = "!" + candidate

        # match tlds: 
        if (exception_candidate in tlds):
            return ".".join(url_elements[i:]) 
        if (candidate in tlds or wildcard_candidate in tlds):
            return ".".join(url_elements[i-1:])
            # returns "abcde.co.uk"

    logger.debug(url_elements)
    raise ValueError("Domain not in global list of TLDs")

def extract_domains(file_contents, fail_email, filename):
    tlds = load_tlds()
    exclusions = load_exclusions()
    domain_list = set()
    excluded_domains = set()
    ln = 0
    failed_domains = []
    for url in file_contents:
        ln += 1
        if url[0] in '/\n':
            continue
        # logger.debug(url.strip())
        try:
            url = url.strip()
            if iponly_re.match(url) is not None:
                raise ValueError('IP only - no domain to extract')
            elif url.startswith('javascript:'):
                raise ValueError('Javascript hook')
            domain = remove_subdomains(url.strip(), tlds)

            if domain not in exclusions:
                domain_list.add(domain)
            else:
                excluded_domains.add(domain)
        except ValueError as e:
            failed_domains.append((ln, url.strip(), str(e)))


    if len(failed_domains) > 0:
        error_email = 'The following domains failed on the file "%s":\n\n' % filename
        for fd in failed_domains:
            error_email += 'Line %d: %s (%s)\n' % (fd[0], fd[1], fd[2])
        logger.debug(error_email)
        send_mail('Domain Checker: Failed Domains', error_email, 'noreply@domain.com', [fail_email])
    logger.debug('Excluded (%d) domains: [%s]' % (len(excluded_domains), ', '.join(excluded_domains)))
    return (domain_list, excluded_domains)

def index(request):
    fdir = os.path.dirname(__file__)
    tlds = load_tlds()
    exclusions = load_exclusions()
    domain_list = set()
    excluded_domains = set()
    urlc = 0
    if request.method == 'POST':
        form = URLFileForm(request.POST, request.FILES)
        if form.is_valid():
            for url in request.FILES['file']:
                if url[0] in '/\n':
                    continue
                urlc += 1
                # logger.debug(url.strip())
                domain = remove_subdomains(url.strip(), tlds)
                if domain not in exclusions:
                    domain_list.add(domain)
                else:
                    excluded_domains.add(domain)
            logger.debug('Excluded (%d) domains: [%s]' % (len(excluded_domains), ', '.join(excluded_domains)))
    return render(request, 'main/index.html', {'domain_list' : sorted(domain_list), 'form' : URLFileForm(request.POST), 'urlc' : urlc, 'excluded_domains': excluded_domains,})

# TODO: Should properly use CSRF tokens for this
@csrf_exempt
def check_login(request):
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
    if request.user.is_authenticated():
        logout(request)
    return redirect('/')

@login_required(login_url='/')
def profile(request):
    if not request.user.is_authenticated():
        return redirect('/')
    profile_message = None
    profile_messagetype = None
    if request.session.has_key('profile_message'):
        profile_message = request.session['profile_message']
        profile_messagetype = request.session['profile_messagetype']
        del request.session['profile_message']
        del request.session['profile_messagetype']
    uploadform = URLFileForm(request.POST, request.FILES)
    projects = UserProject.objects.filter(user_id=request.user.id)
    for project in projects:
        project.file = UploadedFile.objects.get(project_id=project.id)
        logger.debug('Filename: %s' % project.file.filename)
        project.domains = ProjectDomain.objects.filter(project_id=project.id)
    exclusions = None
    preserved = None
    staff = None
    if request.user.is_staff:
        exclusions = '\n'.join([e.domain for e in ExcludedDomain.objects.all()])
        preserved = '\n'.join([p.domain for p in PreservedDomain.objects.all()])
    if request.user.is_superuser:
        staff = '\n'.join([u.username for u in User.objects.filter(is_staff=True)])
    return render(request, 
        'main/profile.html', 
        {
            'user' : request.user, 
            'projects' : projects, 
            'uploadform' : uploadform, 
            'profile_message' : profile_message, 
            'profile_messagetype' : profile_messagetype, 
            'exclusions' : exclusions, 
            'preserved' : preserved,
            'staff' : staff})

def upload_project(request):
    if not request.user.is_authenticated():
        return redirect('/')
    if request.method == 'POST':
        uploadform = URLFileForm(request.POST, request.FILES)
        logger.debug('Attempting to upload project...')
        if uploadform.is_valid():
            logger.debug('Form is valid.')
            (domain_list, excluded_domains) = extract_domains(request.FILES['file'], request.user.email, request.FILES['file'].name)
            projectdomains = []
            project = UserProject(is_complete=False, is_paused=False, updated=timezone.now(), user_id=request.user.id)
            project.save()
            projectfile = UploadedFile(filename=request.FILES['file'].name, filedata=request.FILES['file'].read(), project_id=project.id)
            for domain in domain_list:
                projectdomains.append(ProjectDomain(domain=domain, subdomains_preserved=False, is_checked=False, is_available=False, last_checked=timezone.now(), project_id=project.id))
            projectfile.save()
            [pd.save() for pd in projectdomains]
        else:
            logger.debug(uploadform.errors)
    return redirect('/profile', message='Project added.  You will be emailed when all domains are checked.', messagetype='success')

def change_details(request):
    if not request.user.is_authenticated():
        return redirect('/')
    first_name = request.GET['first_name']
    last_name = request.GET['last_name']
    request.user.first_name = first_name
    request.user.last_name = last_name
    request.user.save()
    request.session['profile_message'] = 'Your details have been successfully updated'
    request.session['profile_messagetype'] = 'success'
    return redirect('/profile')

def change_email(request):
    if not request.user.is_authenticated():
        return redirect('/')
    email = request.GET['email1']
    request.user.email = email
    request.user.save()
    request.session['profile_message'] = 'Your email has been successfully updated'
    request.session['profile_messagetype'] = 'success'
    return redirect('/profile')

def change_password(request):
    if not request.user.is_authenticated():
        return redirect('/')
    if not request.method == 'GET':
        return redirect('/profile')
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
    return redirect('/profile')

def delete_project(request):
    if not request.user.is_authenticated():
        return redirect('/')
    pid = int(request.GET['pid'])
    project = UserProject.objects.get(id=pid)
    if project.user_id != request.user.id:
        return redirect('/')
    pname = UploadedFile.objects.get(project_id=project.id).filename
    deep_delete_project(project)
    request.session['profile_message'] = 'Project "%s" has been deleted.' % pname
    request.session['profile_messagetype'] = 'success'
    return redirect('/profile')

@transaction.atomic
def update_admin(request):
    if not request.user.is_authenticated() or not request.user.is_staff or request.method != 'POST':
        return redirect('/')
    exclusions = request.POST['exclusions']
    preserved = request.POST['preserved']

    # Clear old values
    ExcludedDomain.objects.all().delete()
    PreservedDomain.objects.all().delete()

    for e in exclusions.split('\n'):
        e = e.strip()
        if len(e) == 0:
            continue
        ed = ExcludedDomain(domain=e)
        ed.save()

    for p in preserved.split('\n'):
        p = p.strip()
        if len(p) == 0:
            continue
        pd = PreservedDomain(domain=p)
        pd.save()

    if request.user.is_superuser:
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
    return redirect('/profile')

def register_user(request):
    if request.method != 'POST':
        return redirect('/')

    username = request.POST['username']
    first_name = request.POST['first_name']
    last_name = request.POST['last_name']
    email = request.POST['email']
    password = request.POST['password']

    user = User.objects.create_user(username, email, password, first_name=first_name, last_name=last_name)
    user.save()

    user = authenticate(username=username, password=password)
    login(request, user)

    return redirect('/profile')

@csrf_exempt
def check_username(request):
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
        return redirect('/')

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
