from django import forms
from .models import ClinicSettings, Attendance, QueueTicket, PromotionalProduct


class ClinicSettingsForm(forms.ModelForm):
    class Meta:
        model = ClinicSettings
        fields = ['clinic_name', 'address', 'phone', 'email', 'website', 'logo',
                  'tax_registration', 'operating_hours', 'invoice_prefix',
                  'invoice_terms', 'default_tax_rate', 'currency']
        widgets = {
            'clinic_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'tax_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'operating_hours': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'invoice_prefix': forms.TextInput(attrs={'class': 'form-control'}),
            'invoice_terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'default_tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
        }


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['staff', 'date', 'check_in', 'check_out', 'status', 'notes']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'check_in': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class QueueTicketForm(forms.ModelForm):
    class Meta:
        model = QueueTicket
        fields = ['patient_name', 'doctor', 'room']
        widgets = {
            'patient_name': forms.TextInput(attrs={'class': 'form-control'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PromotionalProductForm(forms.ModelForm):
    class Meta:
        model = PromotionalProduct
        fields = ['name', 'description', 'original_price', 'promotional_price',
                  'discount_percentage', 'start_date', 'end_date', 'is_active', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'original_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'promotional_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
