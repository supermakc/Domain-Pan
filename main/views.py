# Create your views here.
from django.http import HttpResponse
from django.shortcuts import render
from urlparse import urlparse
from forms import URLFileForm

import os

def load_tlds(filename):
    tldf = open(filename)
    tlds = [line.strip() for line in tldf if line[0] not in "/\n"]
    tldf.close()
    return tlds

def get_domain(url):
    tlds = load_tlds("effective_tld_names.dat.txt")

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
    domain_list = set()
    if request.method == 'POST':
        form = URLFileForm(request.POST, request.FILES)
        if form.is_valid():
            urls = request.FILES['file'].read().split('\n')
            for url in urls:
                # domain = urlparse(url).netloc
                domain = get_domain(url)
                domain_list.add(domain)
    return render(request, 'main/index.html', {'domain_list' : sorted(domain_list), 'form' : URLFileForm(request.POST), 'cwd' : os.getcwd()})
