from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime, timedelta
import uuid
from .models import Patient, Visit, Consultation, Prescription, Appointment, LabResult, Immunization
from .forms import PatientForm, VisitForm, ConsultationForm, PrescriptionForm, AppointmentForm, LabResultForm, ImmunizationForm
from accounts.models import User


def generate_patient_id():
    return f"P{timezone.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:4].upper()}"


def generate_visit_number():
    return f"V{timezone.now().strftime('%Y%m%d%H%M%S')}"


@login_required
def patient_list(request):
    query = request.GET.get('q', '')
    patients = Patient.objects.filter(is_active=True)
    if query:
        patients = patients.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(patient_id__icontains=query) |
            Q(phone__icontains=query)
        )
    return render(request, 'patients/patient_list.html', {'patients': patients, 'query': query})


@login_required
def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.patient_id = generate_patient_id()
            patient.save()
            form.save_m2m()
            messages.success(request, f'Patient {patient.full_name} registered successfully.')
            return redirect('patients:patient_detail', pk=patient.pk)
    else:
        form = PatientForm()
    return render(request, 'patients/patient_form.html', {'form': form, 'title': 'Register New Patient'})


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    visits = patient.visits.all()[:10]
    appointments = patient.appointments.filter(appointment_date__gte=timezone.now().date())[:5]
    return render(request, 'patients/patient_detail.html', {
        'patient': patient,
        'visits': visits,
        'appointments': appointments
    })


@login_required
def patient_edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, f'Patient {patient.full_name} updated successfully.')
            return redirect('patients:patient_detail', pk=patient.pk)
    else:
        form = PatientForm(instance=patient)
    return render(request, 'patients/patient_form.html', {'form': form, 'title': 'Edit Patient', 'patient': patient})


@login_required
def patient_history(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    visits = patient.visits.all()
    lab_results = patient.lab_results.all()
    immunizations = patient.immunizations.all()
    return render(request, 'patients/patient_history.html', {
        'patient': patient,
        'visits': visits,
        'lab_results': lab_results,
        'immunizations': immunizations
    })


@login_required
def visit_list(request):
    date_filter = request.GET.get('date', timezone.now().date().isoformat())
    visits = Visit.objects.filter(visit_date__date=date_filter).order_by('-visit_date')
    return render(request, 'patients/visit_list.html', {'visits': visits, 'date_filter': date_filter})


@login_required
def visit_create(request, patient_id=None):
    initial = {}
    if patient_id:
        patient = get_object_or_404(Patient, pk=patient_id)
        initial['patient'] = patient
    
    if request.method == 'POST':
        form = VisitForm(request.POST)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.visit_number = generate_visit_number()
            visit.created_by = request.user
            today_visits = Visit.objects.filter(visit_date__date=timezone.now().date()).count()
            visit.queue_number = today_visits + 1
            visit.save()
            messages.success(request, f'Visit registered. Queue number: {visit.queue_number}')
            return redirect('patients:visit_detail', pk=visit.pk)
    else:
        initial['visit_date'] = timezone.now()
        form = VisitForm(initial=initial)
        form.fields['doctor'].queryset = User.objects.filter(role='doctor', is_active=True)
    return render(request, 'patients/visit_form.html', {'form': form, 'title': 'Register Visit'})


@login_required
def visit_detail(request, pk):
    visit = get_object_or_404(Visit, pk=pk)
    consultation = getattr(visit, 'consultation', None)
    return render(request, 'patients/visit_detail.html', {'visit': visit, 'consultation': consultation})


@login_required
def consultation_create(request, visit_id):
    visit = get_object_or_404(Visit, pk=visit_id)
    if hasattr(visit, 'consultation'):
        return redirect('patients:consultation_edit', pk=visit.consultation.pk)
    
    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.visit = visit
            consultation.doctor = request.user
            consultation.save()
            visit.status = 'in_progress'
            visit.save()
            messages.success(request, 'Consultation saved successfully.')
            return redirect('patients:consultation_detail', pk=consultation.pk)
    else:
        form = ConsultationForm()
    return render(request, 'patients/consultation_form.html', {'form': form, 'visit': visit, 'title': 'New Consultation'})


@login_required
def consultation_detail(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    prescriptions = consultation.prescriptions.all()
    return render(request, 'patients/consultation_detail.html', {'consultation': consultation, 'prescriptions': prescriptions})


@login_required
def consultation_edit(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    if request.method == 'POST':
        form = ConsultationForm(request.POST, instance=consultation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Consultation updated successfully.')
            return redirect('patients:consultation_detail', pk=consultation.pk)
    else:
        form = ConsultationForm(instance=consultation)
    return render(request, 'patients/consultation_form.html', {'form': form, 'visit': consultation.visit, 'title': 'Edit Consultation'})


@login_required
def prescription_add(request, consultation_id):
    consultation = get_object_or_404(Consultation, pk=consultation_id)
    if request.method == 'POST':
        form = PrescriptionForm(request.POST)
        if form.is_valid():
            prescription = form.save(commit=False)
            prescription.consultation = consultation
            prescription.save()
            messages.success(request, 'Prescription added successfully.')
            return redirect('patients:consultation_detail', pk=consultation.pk)
    else:
        form = PrescriptionForm()
    return render(request, 'patients/prescription_form.html', {'form': form, 'consultation': consultation})


@login_required
def appointment_list(request):
    date_filter = request.GET.get('date', timezone.now().date().isoformat())
    doctor_filter = request.GET.get('doctor', '')
    
    appointments = Appointment.objects.filter(appointment_date=date_filter)
    if doctor_filter:
        appointments = appointments.filter(doctor_id=doctor_filter)
    
    doctors = User.objects.filter(role='doctor', is_active=True)
    return render(request, 'patients/appointment_list.html', {
        'appointments': appointments,
        'date_filter': date_filter,
        'doctors': doctors,
        'doctor_filter': doctor_filter
    })


@login_required
def appointment_create(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.created_by = request.user
            appointment.save()
            messages.success(request, 'Appointment scheduled successfully.')
            return redirect('patients:appointment_list')
    else:
        form = AppointmentForm()
        form.fields['doctor'].queryset = User.objects.filter(role='doctor', is_active=True)
    return render(request, 'patients/appointment_form.html', {'form': form, 'title': 'Schedule Appointment'})


@login_required
def appointment_edit(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment updated successfully.')
            return redirect('patients:appointment_list')
    else:
        form = AppointmentForm(instance=appointment)
        form.fields['doctor'].queryset = User.objects.filter(role='doctor', is_active=True)
    return render(request, 'patients/appointment_form.html', {'form': form, 'title': 'Edit Appointment'})


@login_required
def appointment_status(request, pk, status):
    appointment = get_object_or_404(Appointment, pk=pk)
    if status in ['completed', 'cancelled', 'no_show']:
        appointment.status = status
        appointment.save()
        messages.success(request, f'Appointment marked as {status}.')
    return redirect('patients:appointment_list')


@login_required
def calendar_view(request):
    doctors = User.objects.filter(role='doctor', is_active=True)
    return render(request, 'patients/calendar.html', {'doctors': doctors})


@login_required
def calendar_events(request):
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')
    doctor = request.GET.get('doctor', '')
    
    appointments = Appointment.objects.all()
    if start:
        appointments = appointments.filter(appointment_date__gte=start)
    if end:
        appointments = appointments.filter(appointment_date__lte=end)
    if doctor:
        appointments = appointments.filter(doctor_id=doctor)
    
    events = []
    for apt in appointments:
        events.append({
            'id': apt.id,
            'title': f"{apt.patient.full_name} - {apt.reason[:30]}",
            'start': f"{apt.appointment_date}T{apt.appointment_time}",
            'color': '#28a745' if apt.status == 'completed' else '#007bff' if apt.status == 'scheduled' else '#dc3545'
        })
    return JsonResponse(events, safe=False)


@login_required
def complete_visit(request, pk):
    visit = get_object_or_404(Visit, pk=pk)
    visit.status = 'completed'
    visit.save()
    messages.success(request, 'Visit marked as completed.')
    return redirect('patients:visit_detail', pk=pk)
