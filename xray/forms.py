from django import forms
from .models import XrayStudy, XrayImage, XrayDocument, XrayReport
from patients.models import Patient


class XrayStudyForm(forms.ModelForm):
    patient_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search patient by name or IC...',
            'autocomplete': 'off'
        })
    )
    
    class Meta:
        model = XrayStudy
        fields = ['patient', 'body_region', 'view_type', 'side', 'clinical_indication', 
                  'clinical_history', 'priority', 'notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'body_region': forms.Select(attrs={'class': 'form-select'}),
            'view_type': forms.Select(attrs={'class': 'form-select'}),
            'side': forms.Select(attrs={'class': 'form-select'}),
            'clinical_indication': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'clinical_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class XrayImageForm(forms.ModelForm):
    class Meta:
        model = XrayImage
        fields = ['image', 'description']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional description...'}),
        }


class XrayDocumentForm(forms.ModelForm):
    class Meta:
        model = XrayDocument
        fields = ['document', 'doc_type', 'title']
        widgets = {
            'document': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,.txt'}),
            'doc_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Document title...'}),
        }


class XrayReportForm(forms.ModelForm):
    class Meta:
        model = XrayReport
        fields = ['technique', 'findings', 'impression', 'recommendations']
        widgets = {
            'technique': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'findings': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'impression': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'recommendations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
