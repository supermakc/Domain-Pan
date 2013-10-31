# Create your views here.
from django.http import HttpResponse
from django.shortcuts import render
from urlparse import urlparse
from forms import URLFileForm

def index(request):
    domain_list = set()
    if request.method == 'POST':
        form = URLFileForm(request.POST, request.FILES)
        if form.is_valid():
            urls = request.FILES['file'].read().split('\n')
            for url in urls:
                domain = urlparse(url).netloc
                if domain.startswith('www.'):
                    domain = domain[4:]
                domain_list.add(domain)
    return render(request, 'main/index.html', {'domain_list' : sorted(domain_list), 'form' : URLFileForm(request.POST)})
