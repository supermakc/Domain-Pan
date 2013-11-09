from django import forms

class URLFileForm(forms.Form):
    file = forms.FileField(widget=forms.FileInput(attrs={'class':''}))
