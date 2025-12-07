from django import forms
from .models import AIConfig


class AIConfigForm(forms.ModelForm):
    class Meta:
        model = AIConfig
        fields = [
            'is_enabled', 'model_name', 'max_tokens', 'temperature',
            'triage_enabled', 'consultation_notes_enabled', 'medical_summary_enabled',
            'referral_letter_enabled', 'stock_suggestion_enabled', 'dashboard_insights_enabled',
            'revenue_forecast_enabled', 'anomaly_detection_enabled', 'assistant_enabled',
        ]
        widgets = {
            'model_name': forms.Select(choices=[
                ('gpt-4o-mini', 'GPT-4o Mini (Cost Effective)'),
                ('gpt-4o', 'GPT-4o (Best Quality)'),
                ('gpt-4-turbo', 'GPT-4 Turbo'),
                ('gpt-3.5-turbo', 'GPT-3.5 Turbo (Fastest)'),
            ], attrs={'class': 'form-select'}),
            'max_tokens': forms.NumberInput(attrs={'class': 'form-control', 'min': 100, 'max': 4000}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 1, 'step': 0.1}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'


class TriageForm(forms.Form):
    complaint = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter patient complaint or symptoms...'
        }),
        label='Patient Complaint'
    )


class ConsultationNotesForm(forms.Form):
    raw_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Enter raw clinical notes to structure...'
        }),
        label='Raw Clinical Notes'
    )


class ReferralLetterForm(forms.Form):
    referred_to = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specialist name or hospital'}),
        label='Referred To'
    )
    specialty = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Cardiology, Orthopedics'}),
        label='Specialty'
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Reason for referral'}),
        label='Reason for Referral'
    )
    clinical_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Relevant clinical notes'}),
        required=False,
        label='Clinical Notes'
    )
    diagnosis = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Current diagnosis'}),
        required=False,
        label='Diagnosis'
    )
    treatment = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Treatment given so far'}),
        required=False,
        label='Treatment Given'
    )


class AssistantForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Ask me anything about the clinic system...'
        }),
        label='Your Question'
    )
