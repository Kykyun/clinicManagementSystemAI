from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, F
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime, timedelta
import uuid
from .models import Patient, Visit, Consultation, Prescription, Appointment, LabResult, Immunization, Triage
from .forms import PatientForm, VisitForm, ConsultationForm, PrescriptionForm, AppointmentForm, LabResultForm, ImmunizationForm, CheckInForm, TriageForm
from accounts.models import User
from accounts.decorators import doctor_required, clinical_staff_required, reception_or_higher, nurse_required, pharmacy_required, finance_access_required
from setup_app.models import Panel, Medicine


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
@reception_or_higher
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
@reception_or_higher
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
@clinical_staff_required
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
@reception_or_higher
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
@doctor_required
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
    
    past_visits = Visit.objects.filter(
        patient=visit.patient,
        status='completed'
    ).exclude(pk=visit.pk).select_related('consultation').order_by('-visit_date')[:5]
    
    return render(request, 'patients/consultation_form.html', {
        'form': form, 
        'visit': visit, 
        'title': 'New Consultation',
        'past_visits': past_visits
    })


@login_required
@clinical_staff_required
def consultation_detail(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    prescriptions = consultation.prescriptions.all()
    return render(request, 'patients/consultation_detail.html', {'consultation': consultation, 'prescriptions': prescriptions})


@login_required
@doctor_required
def consultation_edit(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    visit = consultation.visit
    if request.method == 'POST':
        form = ConsultationForm(request.POST, instance=consultation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Consultation updated successfully.')
            return redirect('patients:consultation_detail', pk=consultation.pk)
    else:
        form = ConsultationForm(instance=consultation)
    
    past_visits = Visit.objects.filter(
        patient=visit.patient,
        status='completed'
    ).exclude(pk=visit.pk).select_related('consultation').order_by('-visit_date')[:5]
    
    return render(request, 'patients/consultation_form.html', {
        'form': form, 
        'visit': visit, 
        'title': 'Edit Consultation',
        'past_visits': past_visits
    })


@login_required
@doctor_required
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
def add_prescriptions_bulk(request, consultation_id):
    import json
    from setup_app.models import Medicine
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
    
    try:
        consultation = get_object_or_404(Consultation, pk=consultation_id)
        data = json.loads(request.body)
        prescriptions_data = data.get('prescriptions', [])
        
        if not prescriptions_data:
            return JsonResponse({'success': False, 'error': 'No prescriptions provided'}, status=400)
        
        added_count = 0
        for rx in prescriptions_data:
            medicine = None
            if rx.get('medicine_id'):
                medicine = Medicine.objects.filter(id=rx['medicine_id']).first()
            if not medicine:
                medicine = Medicine.objects.filter(name__iexact=rx.get('medicine_name', '')).first()
            if not medicine:
                medicine = Medicine.objects.filter(name__icontains=rx.get('medicine_name', '')).first()
            
            if medicine:
                Prescription.objects.create(
                    consultation=consultation,
                    medicine=medicine,
                    dosage=rx.get('dosage', ''),
                    frequency=rx.get('frequency', ''),
                    duration=rx.get('duration', ''),
                    quantity=rx.get('quantity', 1),
                    instructions=rx.get('instructions', ''),
                    is_dispensed=False,
                )
                added_count += 1
        
        return JsonResponse({'success': True, 'added_count': added_count})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def appointment_list(request):
    date_filter = request.GET.get('date', '')
    doctor_filter = request.GET.get('doctor', '')
    
    appointments = Appointment.objects.all().order_by('appointment_date', 'appointment_time')
    if date_filter:
        appointments = appointments.filter(appointment_date=date_filter)
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
@reception_or_higher
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
@reception_or_higher
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
@reception_or_higher
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
        start_date = start.split('T')[0]
        appointments = appointments.filter(appointment_date__gte=start_date)
    if end:
        end_date = end.split('T')[0]
        appointments = appointments.filter(appointment_date__lte=end_date)
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
@clinical_staff_required
def complete_visit(request, pk):
    visit = get_object_or_404(Visit, pk=pk)
    visit.status = 'completed'
    visit.save()
    messages.success(request, 'Visit marked as completed.')
    return redirect('patients:visit_detail', pk=pk)


# ==================== RECEPTION DASHBOARD ====================

@login_required
@reception_or_higher
def reception_dashboard(request):
    today = timezone.now().date()
    
    todays_appointments = Appointment.objects.filter(
        appointment_date=today
    ).select_related('patient', 'doctor').order_by('appointment_time')
    
    todays_visits = Visit.objects.filter(
        visit_date__date=today
    ).select_related('patient', 'doctor').order_by('queue_number')
    
    waiting_count = todays_visits.filter(status__in=['waiting_triage', 'waiting_doctor']).count()
    in_progress_count = todays_visits.filter(status='in_consultation').count()
    completed_count = todays_visits.filter(status='completed').count()
    
    doctors = User.objects.filter(role='doctor', is_active=True)
    panels = Panel.objects.filter(is_active=True)
    
    context = {
        'todays_appointments': todays_appointments,
        'todays_visits': todays_visits,
        'waiting_count': waiting_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'doctors': doctors,
        'panels': panels,
        'today': today,
    }
    return render(request, 'patients/reception_dashboard.html', context)


@login_required
@reception_or_higher
def patient_search_api(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    patients = Patient.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(patient_id__icontains=query) |
        Q(phone__icontains=query) |
        Q(id_number__icontains=query)
    ).filter(is_active=True)[:10]
    
    results = []
    for p in patients:
        results.append({
            'id': p.id,
            'patient_id': p.patient_id,
            'name': p.full_name,
            'phone': p.phone,
            'dob': p.date_of_birth.strftime('%Y-%m-%d'),
            'age': p.age,
            'gender': p.gender,
            'panel': p.panel.name if p.panel else None,
        })
    return JsonResponse({'results': results})


@login_required
@reception_or_higher
def patient_check_in(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    
    if request.method == 'POST':
        form = CheckInForm(request.POST)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.patient = patient
            visit.visit_number = generate_visit_number()
            visit.visit_date = timezone.now()
            visit.created_by = request.user
            visit.status = 'waiting_triage'
            today_visits = Visit.objects.filter(visit_date__date=timezone.now().date()).count()
            visit.queue_number = today_visits + 1
            visit.save()
            messages.success(request, f'Patient checked in. Queue number: {visit.queue_number}')
            return redirect('patients:reception_dashboard')
    else:
        initial = {}
        if patient.panel:
            initial['payer_type'] = 'corporate'
        form = CheckInForm(initial=initial)
        form.fields['doctor'].queryset = User.objects.filter(role='doctor', is_active=True)
    
    recent_visits = patient.visits.all()[:5]
    
    return render(request, 'patients/check_in.html', {
        'form': form,
        'patient': patient,
        'recent_visits': recent_visits,
    })


@login_required
@reception_or_higher  
def walk_in_registration(request):
    if request.method == 'POST':
        patient_form = PatientForm(request.POST)
        if patient_form.is_valid():
            patient = patient_form.save(commit=False)
            patient.patient_id = generate_patient_id()
            patient.save()
            patient_form.save_m2m()
            messages.success(request, f'Patient {patient.full_name} registered.')
            return redirect('patients:patient_check_in', patient_id=patient.pk)
    else:
        patient_form = PatientForm()
    
    return render(request, 'patients/walk_in_registration.html', {
        'form': patient_form,
    })


# ==================== NURSE DASHBOARD ====================

@login_required
@clinical_staff_required
def nurse_dashboard(request):
    today = timezone.now().date()
    
    waiting_triage = Visit.objects.filter(
        visit_date__date=today,
        status='waiting_triage'
    ).select_related('patient', 'doctor').order_by('queue_number')
    
    in_triage = Visit.objects.filter(
        visit_date__date=today,
        status='waiting_doctor'
    ).select_related('patient', 'doctor', 'triage').order_by('-updated_at')[:10]
    
    context = {
        'waiting_triage': waiting_triage,
        'in_triage': in_triage,
        'today': today,
    }
    return render(request, 'patients/nurse_dashboard.html', context)


@login_required
@clinical_staff_required
def start_triage(request, visit_id):
    visit = get_object_or_404(Visit, pk=visit_id)
    
    if hasattr(visit, 'triage'):
        return redirect('patients:edit_triage', visit_id=visit_id)
    
    if request.method == 'POST':
        form = TriageForm(request.POST)
        if form.is_valid():
            triage = form.save(commit=False)
            triage.visit = visit
            triage.performed_by = request.user
            
            if visit.patient.allergies.exists():
                triage.allergy_flag = True
            
            triage.save()
            visit.status = 'waiting_doctor'
            visit.save()
            messages.success(request, 'Triage completed. Patient ready for doctor.')
            return redirect('patients:nurse_dashboard')
    else:
        form = TriageForm()
    
    return render(request, 'patients/triage_form.html', {
        'form': form,
        'visit': visit,
        'title': 'Triage',
    })


@login_required
@clinical_staff_required
def edit_triage(request, visit_id):
    visit = get_object_or_404(Visit, pk=visit_id)
    triage = get_object_or_404(Triage, visit=visit)
    
    if request.method == 'POST':
        form = TriageForm(request.POST, instance=triage)
        if form.is_valid():
            form.save()
            messages.success(request, 'Triage updated.')
            return redirect('patients:nurse_dashboard')
    else:
        form = TriageForm(instance=triage)
    
    return render(request, 'patients/triage_form.html', {
        'form': form,
        'visit': visit,
        'triage': triage,
        'title': 'Edit Triage',
    })


# ==================== DOCTOR DASHBOARD ====================

@login_required
@doctor_required
def doctor_dashboard(request):
    today = timezone.now().date()
    doctor_filter = request.GET.get('doctor', '')
    
    visits = Visit.objects.filter(
        visit_date__date=today,
        status__in=['waiting_doctor', 'in_consultation']
    ).select_related('patient', 'doctor', 'triage')
    
    if doctor_filter:
        visits = visits.filter(doctor_id=doctor_filter)
    elif request.user.role == 'doctor':
        visits = visits.filter(Q(doctor=request.user) | Q(doctor__isnull=True))
    
    visits = visits.order_by('queue_number')
    
    doctors = User.objects.filter(role='doctor', is_active=True)
    
    waiting_count = visits.filter(status='waiting_doctor').count()
    in_consultation_count = visits.filter(status='in_consultation').count()
    
    context = {
        'visits': visits,
        'doctors': doctors,
        'doctor_filter': doctor_filter,
        'waiting_count': waiting_count,
        'in_consultation_count': in_consultation_count,
        'today': today,
    }
    return render(request, 'patients/doctor_dashboard.html', context)


@login_required
@doctor_required
def start_consultation(request, visit_id):
    visit = get_object_or_404(Visit, pk=visit_id)
    
    if hasattr(visit, 'consultation'):
        return redirect('patients:consultation_edit', pk=visit.consultation.pk)
    
    visit.status = 'in_consultation'
    if not visit.doctor:
        visit.doctor = request.user
    visit.save()
    
    return redirect('patients:consultation_create', visit_id=visit_id)


@login_required
@doctor_required
def complete_consultation(request, consultation_id):
    consultation = get_object_or_404(Consultation, pk=consultation_id)
    visit = consultation.visit
    
    if request.method == 'POST':
        next_status = request.POST.get('next_status', 'ready_for_payment')
        
        if next_status == 'to_pharmacy' and consultation.prescriptions.exists():
            visit.status = 'to_pharmacy'
        elif next_status == 'to_lab':
            visit.status = 'to_lab'
        else:
            visit.status = 'ready_for_payment'
        
        visit.save()
        messages.success(request, f'Consultation completed. Status: {visit.get_status_display()}')
        return redirect('patients:doctor_dashboard')
    
    return render(request, 'patients/complete_consultation.html', {
        'consultation': consultation,
        'visit': visit,
    })


# ==================== PHARMACY DASHBOARD ====================

@login_required
@pharmacy_required
def pharmacy_dashboard(request):
    today = timezone.now().date()
    
    pending_visits = Visit.objects.filter(
        visit_date__date=today,
        status='to_pharmacy'
    ).select_related('patient', 'doctor', 'consultation').order_by('queue_number')
    
    pending_prescriptions = []
    for visit in pending_visits:
        if hasattr(visit, 'consultation'):
            prescriptions = visit.consultation.prescriptions.filter(is_dispensed=False)
            if prescriptions.exists():
                pending_prescriptions.append({
                    'visit': visit,
                    'prescriptions': prescriptions,
                    'total_items': prescriptions.count(),
                })
    
    low_stock_medicines = Medicine.objects.filter(
        stock_quantity__lte=F('minimum_stock')
    ).order_by('stock_quantity')[:10]
    
    context = {
        'pending_prescriptions': pending_prescriptions,
        'low_stock_medicines': low_stock_medicines,
        'today': today,
    }
    return render(request, 'patients/pharmacy_dashboard.html', context)


@login_required
@pharmacy_required
def dispense_prescriptions(request, visit_id):
    visit = get_object_or_404(Visit, pk=visit_id)
    
    if not hasattr(visit, 'consultation'):
        messages.error(request, 'No consultation found for this visit.')
        return redirect('patients:pharmacy_dashboard')
    
    prescriptions = visit.consultation.prescriptions.all()
    
    if request.method == 'POST':
        dispensed_ids = request.POST.getlist('dispensed')
        
        for prescription in prescriptions:
            if str(prescription.id) in dispensed_ids:
                if not prescription.is_dispensed:
                    prescription.is_dispensed = True
                    prescription.dispensed_at = timezone.now()
                    prescription.dispensed_by = request.user
                    prescription.save()
                    
                    if prescription.medicine:
                        medicine = prescription.medicine
                        medicine.stock_quantity = max(0, medicine.stock_quantity - prescription.quantity)
                        medicine.save()
        
        all_dispensed = not prescriptions.filter(is_dispensed=False).exists()
        if all_dispensed:
            visit.status = 'ready_for_payment'
            visit.save()
            messages.success(request, 'All prescriptions dispensed. Patient ready for payment.')
        else:
            messages.success(request, 'Prescriptions updated.')
        
        return redirect('patients:pharmacy_dashboard')
    
    return render(request, 'patients/dispense_prescriptions.html', {
        'visit': visit,
        'prescriptions': prescriptions,
    })


# ==================== QUEUE DISPLAY ====================

def queue_display(request):
    today = timezone.now().date()
    
    active_visits = Visit.objects.filter(
        visit_date__date=today,
        status__in=['waiting_triage', 'waiting_doctor', 'in_consultation', 'to_pharmacy', 'to_lab']
    ).select_related('patient', 'doctor').order_by('queue_number')
    
    queue_items = []
    for visit in active_visits:
        initials = ''
        if visit.patient.first_name:
            initials += visit.patient.first_name[0].upper()
        if visit.patient.last_name:
            initials += visit.patient.last_name[0].upper()
        
        queue_items.append({
            'queue_number': visit.queue_number,
            'initials': initials or 'P',
            'doctor': visit.doctor.get_full_name() if visit.doctor else 'Any',
            'room': visit.room or '-',
            'status': visit.get_status_display(),
            'status_class': visit.status_display_class,
        })
    
    context = {
        'queue_items': queue_items,
        'today': today,
    }
    return render(request, 'patients/queue_display.html', context)
