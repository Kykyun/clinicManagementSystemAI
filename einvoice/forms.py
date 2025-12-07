from django import forms
from .models import EInvoiceConfig, EInvoiceDocument


class EInvoiceConfigForm(forms.ModelForm):
    client_secret = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        required=False,
        help_text="Leave empty to keep existing secret"
    )

    class Meta:
        model = EInvoiceConfig
        fields = [
            'is_active', 'environment', 'client_id', 'client_secret',
            'taxpayer_tin', 'clinic_name', 'clinic_brn',
            'clinic_address_line1', 'clinic_address_line2',
            'clinic_city', 'clinic_state', 'clinic_postcode', 'clinic_country',
            'clinic_phone', 'clinic_email'
        ]
        widgets = {
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'environment': forms.Select(attrs={'class': 'form-select'}),
            'client_id': forms.TextInput(attrs={'class': 'form-control'}),
            'taxpayer_tin': forms.TextInput(attrs={'class': 'form-control'}),
            'clinic_name': forms.TextInput(attrs={'class': 'form-control'}),
            'clinic_brn': forms.TextInput(attrs={'class': 'form-control'}),
            'clinic_address_line1': forms.TextInput(attrs={'class': 'form-control'}),
            'clinic_address_line2': forms.TextInput(attrs={'class': 'form-control'}),
            'clinic_city': forms.TextInput(attrs={'class': 'form-control'}),
            'clinic_state': forms.TextInput(attrs={'class': 'form-control'}),
            'clinic_postcode': forms.TextInput(attrs={'class': 'form-control'}),
            'clinic_country': forms.TextInput(attrs={'class': 'form-control'}),
            'clinic_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'clinic_email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not self.cleaned_data.get('client_secret'):
            if self.instance.pk:
                instance.client_secret = EInvoiceConfig.objects.get(pk=self.instance.pk).client_secret
        if commit:
            instance.save()
        return instance


class CancelEInvoiceForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=True,
        help_text="Provide a reason for cancellation"
    )


class ValidateTINForm(forms.Form):
    tin = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter TIN'})
    )
    id_type = forms.ChoiceField(
        choices=[
            ('BRN', 'Business Registration Number'),
            ('NRIC', 'NRIC'),
            ('PASSPORT', 'Passport'),
            ('ARMY', 'Army ID'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='BRN'
    )
    id_value = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ID Value (optional)'})
    )


class EInvoiceDocumentForm(forms.ModelForm):
    class Meta:
        model = EInvoiceDocument
        fields = ['buyer_tin', 'buyer_name']
        widgets = {
            'buyer_tin': forms.TextInput(attrs={'class': 'form-control'}),
            'buyer_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
