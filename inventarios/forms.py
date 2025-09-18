from django import forms
class CSVUploadForm(forms.Form):
    arquivo = forms.FileField(help_text="CSV com delimitador ;")
