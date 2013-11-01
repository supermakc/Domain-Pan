# Create your views here.
from django.http import HttpResponse
from django.shortcuts import render
from django.core.cache import cache
from forms import URLFileForm

import os, logging
from urlparse import urlparse

TLDS_CACHE_KEY = 'TDLS_CACHE_KEY'

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
    domain_list = set()
    if request.method == 'POST':
        form = URLFileForm(request.POST, request.FILES)
        if form.is_valid():
            urls = request.FILES['file'].read().split('\n')
            for url in urls:
                domain = remove_subdomains(url, tlds)
                domain_list.add(domain)
    return render(request, 'main/index.html', {'domain_list' : sorted(domain_list), 'form' : URLFileForm(request.POST), 'cwd' : os.getcwd()})
