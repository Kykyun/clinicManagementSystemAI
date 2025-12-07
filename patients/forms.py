from django import forms
from django.core.exceptions import ValidationError
from datetime import date, datetime
import re
from .models import Patient, Visit, Consultation, Prescription, Appointment, LabResult, Immunization


def validate_nric(value):
    digits_only = re.sub(r'[^0-9]', '', value)
    if len(digits_only) != 12:
        raise ValidationError('NRIC must be exactly 12 digits.')
    
    year = int(digits_only[0:2])
    month = int(digits_only[2:4])
    day = int(digits_only[4:6])
    
    current_year = date.today().year % 100
    if year <= current_year:
        full_year = 2000 + year
    else:
        full_year = 1900 + year
    
    try:
        dob = date(full_year, month, day)
    except ValueError:
        raise ValidationError('NRIC contains an invalid date (YYMMDD).')
    
    if dob > date.today():
        raise ValidationError('Date of birth from NRIC cannot be in the future.')
    
    return digits_only


def extract_dob_from_nric(nric_digits):
    year = int(nric_digits[0:2])
    month = int(nric_digits[2:4])
    day = int(nric_digits[4:6])
    
    current_year = date.today().year % 100
    if year <= current_year:
        full_year = 2000 + year
    else:
        full_year = 1900 + year
    
    return date(full_year, month, day)


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['first_name', 'last_name', 'id_type', 'id_number', 'date_of_birth', 'gender',
                  'phone', 'email', 'address', 'emergency_contact_name', 
                  'emergency_contact_phone', 'allergies', 'chronic_illnesses', 
                  'blood_type', 'panel', 'notes']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'id_type': forms.Select(attrs={'class': 'form-select'}),
            'id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'allergies': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'chronic_illnesses': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'blood_type': forms.TextInput(attrs={'class': 'form-control'}),
            'panel': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        id_type = cleaned_data.get('id_type')
        id_number = cleaned_data.get('id_number')
        dob = cleaned_data.get('date_of_birth')
        
        if id_type == 'nric' and id_number:
            try:
                nric_digits = validate_nric(id_number)
                cleaned_data['id_number'] = f"{nric_digits[:6]}-{nric_digits[6:8]}-{nric_digits[8:]}"
                nric_dob = extract_dob_from_nric(nric_digits)
                if not dob:
                    cleaned_data['date_of_birth'] = nric_dob
                elif dob != nric_dob:
                    self.add_error('date_of_birth', 
                        f'Date of birth ({dob.strftime("%Y-%m-%d")}) does not match NRIC ({nric_dob.strftime("%Y-%m-%d")}). '
                        'Please correct the NRIC or update the date of birth.')
            except ValidationError as e:
                self.add_error('id_number', e)
        
        elif id_type == 'passport' and id_number:
            if len(id_number) > 20:
                self.add_error('id_number', 'Passport number must be 20 characters or less.')
            if not re.match(r'^[A-Za-z0-9\-/]+$', id_number):
                self.add_error('id_number', 'Passport number can only contain letters, numbers, hyphens, and slashes.')
        
        if dob and dob > date.today():
            self.add_error('date_of_birth', 'Date of birth cannot be in the future.')
        
        return cleaned_data


class VisitForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['patient', 'doctor', 'visit_type', 'visit_date', 'reason']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'visit_type': forms.Select(attrs={'class': 'form-select'}),
            'visit_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = ['chief_complaint', 'history_of_illness', 'examination_findings',
                  'diagnosis', 'treatment_plan', 'notes', 'vitals_bp', 'vitals_pulse',
                  'vitals_temp', 'vitals_weight', 'vitals_height',
                  'mc_issued', 'mc_start_date', 'mc_end_date', 'mc_days', 'mc_reason', 'mc_notes']
        widgets = {
            'chief_complaint': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'history_of_illness': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'examination_findings': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'treatment_plan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'vitals_bp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 120/80'}),
            'vitals_pulse': forms.NumberInput(attrs={'class': 'form-control'}),
            'vitals_temp': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'vitals_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'vitals_height': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'mc_issued': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'mc_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'mc_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'mc_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'mc_reason': forms.Select(attrs={'class': 'form-select'}),
            'mc_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['medicine', 'dosage', 'frequency', 'duration', 'quantity', 'instructions']
        widgets = {
            'medicine': forms.Select(attrs={'class': 'form-select'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control'}),
            'frequency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 3 times daily'}),
            'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 7 days'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'appointment_date', 'appointment_time', 'reason', 'notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'appointment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'appointment_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class LabResultForm(forms.ModelForm):
    class Meta:
        model = LabResult
        fields = ['patient', 'visit', 'lab_test', 'result_value', 'result_unit',
                  'normal_range', 'is_abnormal', 'notes', 'result_file', 'test_date']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'visit': forms.Select(attrs={'class': 'form-select'}),
            'lab_test': forms.Select(attrs={'class': 'form-select'}),
            'result_value': forms.TextInput(attrs={'class': 'form-control'}),
            'result_unit': forms.TextInput(attrs={'class': 'form-control'}),
            'normal_range': forms.TextInput(attrs={'class': 'form-control'}),
            'is_abnormal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'test_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }


class ImmunizationForm(forms.ModelForm):
    class Meta:
        model = Immunization
        fields = ['patient', 'vaccine_name', 'batch_number', 'dose_number',
                  'date_given', 'next_due_date', 'notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'vaccine_name': forms.TextInput(attrs={'class': 'form-control'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'dose_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'date_given': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'next_due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
