# Create your views here.
from django.http import HttpResponse
from django.shortcuts import render
from django.core.cache import cache
from forms import URLFileForm

import os, logging
from urlparse import urlparse

TLDS_CACHE_KEY = 'TDLS_CACHE_KEY'
EXCLUSION_CACHE_KEY = 'EXCLUSION_CACHE_KEY'

logger = logging.getLogger(__name__)

def load_tlds(filename, force_reload=False):
    tlds = cache.get(TLDS_CACHE_KEY, None)
    if tlds is None or force_reload:
        logger.debug('Reloading TLD list...')
        tldf = open(filename)
        tlds = [line.strip() for line in tldf if line[0] not in "/\n"]
        tldf.close()
        cache.set(TLDS_CACHE_KEY, tlds, timeout=None)
        logger.debug('Finished reloading TLD list.')
    else:
        logger.debug('TLD list already in cache...')
    return tlds

def load_exclusions(filename, force_reload=False):
    exclusions = cache.get(EXCLUSION_CACHE_KEY, None)
    if exclusions is None or force_reload:
        logger.debug('Reloading domain exclusion list...')
        exf = open(filename)
        exclusions = [line.strip() for line in exf if line[0] not in '\n']
        cache.set(EXCLUSION_CACHE_KEY, exclusions, timeout=None)
        logger.debug('Finished reloading exclusion list...')
    return exclusions

def remove_subdomains(url, tlds):
    url_elements = urlparse(url)[1].split('.')
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
    tlds = load_tlds("effective_tld_names.dat.txt")
    exclusions = load_exclusions("exclusion_domains.txt")
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
                domain = remove_subdomains(url.strip(), tlds)
                if domain not in exclusions:
                    domain_list.add(domain)
                else:
                    excluded_domains.add(domain)
            logger.debug('Excluded (%d) domains: [%s]' % (len(excluded_domains), ', '.join(excluded_domains)))
    return render(request, 'main/index.html', {'domain_list' : sorted(domain_list), 'form' : URLFileForm(request.POST), 'urlc' : urlc, 'excluded_domains': excluded_domains,})
