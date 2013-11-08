# Create your views here.
from django.http import HttpResponse
from django.shortcuts import render
from django.core.cache import cache
from forms import URLFileForm
from models import TLD, ExcludedDomain

import os, logging, re
from urlparse import urlparse

TLDS_CACHE_KEY = 'TDLS_CACHE_KEY'
EXCLUSION_CACHE_KEY = 'EXCLUSION_CACHE_KEY'

logger = logging.getLogger(__name__)
schemecheck_re = re.compile(r'[^\.]*?//')

def load_tlds():
    return [tld.domain for tld in TLD.objects.filter(included=True)]

def load_exclusions():
    return [exclusion.domain for exclusion in ExcludedDomain.objects.all()]

def remove_subdomains(url, tlds):
    # Checks for presence of // before domain (required by urlparse)
    if schemecheck_re.match(url) == None:
        url = '//'+url

    url_elements = urlparse(url, scheme='http')[1].split('.')
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

    raise ValueError("Domain not in global list of TLDs")


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
