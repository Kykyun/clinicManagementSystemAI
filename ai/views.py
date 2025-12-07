import json
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Sum, Count, F
from django.utils import timezone

from accounts.decorators import admin_required
from .models import AILog, AIConfig
from .forms import AIConfigForm
from .services import (
    ai_suggest_triage,
    ai_structure_consultation_notes,
    ai_summarize_medical_history,
    ai_draft_referral_letter,
    ai_suggest_stock_order,
    ai_generate_dashboard_insights,
    ai_chat_assistant,
    ai_forecast_revenue,
    ai_detect_anomalies,
    ai_suggest_prescriptions,
    AIService,
)


@login_required
@admin_required
def ai_config(request):
    config = AIConfig.get_config()
    
    if request.method == 'POST':
        form = AIConfigForm(request.POST, instance=config)
        if form.is_valid():
            config = form.save(commit=False)
            config.updated_by = request.user
            config.save()
            messages.success(request, 'AI configuration updated successfully.')
            return redirect('ai:config')
    else:
        form = AIConfigForm(instance=config)
    
    service = AIService()
    api_status = 'Connected' if service.client else 'Not configured (missing API key)'
    
    recent_logs = AILog.objects.all()[:10]
    
    today = timezone.now().date()
    stats = {
        'today_requests': AILog.objects.filter(created_at__date=today).count(),
        'today_tokens': AILog.objects.filter(created_at__date=today).aggregate(Sum('tokens_used'))['tokens_used__sum'] or 0,
        'success_rate': 0,
        'avg_response_time': 0,
    }
    
    total_requests = AILog.objects.count()
    if total_requests > 0:
        successful = AILog.objects.filter(status='success').count()
        stats['success_rate'] = round((successful / total_requests) * 100, 1)
        avg_time = AILog.objects.aggregate(avg=Sum('response_time_ms') / Count('id'))
        stats['avg_response_time'] = round(avg_time['avg'] or 0)
    
    context = {
        'form': form,
        'config': config,
        'api_status': api_status,
        'recent_logs': recent_logs,
        'stats': stats,
    }
    return render(request, 'ai/config.html', context)


@login_required
@admin_required
def ai_logs(request):
    logs = AILog.objects.all()
    
    action_filter = request.GET.get('action')
    status_filter = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    if status_filter:
        logs = logs.filter(status=status_filter)
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)
    
    context = {
        'logs': logs[:100],
        'action_choices': AILog.ACTION_CHOICES,
        'status_choices': AILog.STATUS_CHOICES,
        'filters': {
            'action': action_filter,
            'status': status_filter,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    return render(request, 'ai/logs.html', context)


@login_required
@require_http_methods(['POST'])
def api_triage(request):
    try:
        data = json.loads(request.body)
        complaint = data.get('complaint', '')
        
        if not complaint:
            return JsonResponse({'success': False, 'error': 'Complaint text is required'}, status=400)
        
        result = ai_suggest_triage(complaint, user=request.user)
        return JsonResponse(result)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def api_structure_notes(request):
    try:
        data = json.loads(request.body)
        raw_notes = data.get('raw_notes', '')
        
        if not raw_notes:
            return JsonResponse({'success': False, 'error': 'Raw notes are required'}, status=400)
        
        result = ai_structure_consultation_notes(raw_notes, user=request.user)
        return JsonResponse(result)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(['GET', 'POST'])
def api_medical_summary(request, patient_id):
    try:
        from patients.models import Patient, Visit, Consultation, Prescription, LabResult
        
        patient = get_object_or_404(Patient, id=patient_id)
        
        allergies = ', '.join([a.name for a in patient.allergies.all()]) if patient.allergies.exists() else 'None recorded'
        
        recent_visits = Visit.objects.filter(patient=patient).order_by('-visit_date')[:10]
        visits_summary = '; '.join([
            f"{v.visit_date.strftime('%Y-%m-%d')}: {v.visit_type} - {v.complaint or 'N/A'}"
            for v in recent_visits
        ]) if recent_visits else 'No recent visits'
        
        medications = []
        for visit in recent_visits[:5]:
            try:
                consultation = visit.consultation
                prescriptions = Prescription.objects.filter(consultation=consultation)
                for p in prescriptions:
                    medications.append(f"{p.medicine.name} ({p.dosage})")
            except Consultation.DoesNotExist:
                pass
        medications_str = ', '.join(medications[:10]) if medications else 'None recorded'
        
        lab_results = LabResult.objects.filter(patient=patient).order_by('-test_date')[:5]
        labs_str = '; '.join([
            f"{lr.test.name}: {lr.result} ({lr.test_date.strftime('%Y-%m-%d')})"
            for lr in lab_results
        ]) if lab_results else 'None'
        
        age = 'Unknown'
        if patient.date_of_birth:
            today = timezone.now().date()
            age = today.year - patient.date_of_birth.year
            if (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day):
                age -= 1
        
        patient_data = {
            'name': patient.full_name,
            'age': age,
            'gender': patient.gender,
            'allergies': allergies,
            'chronic_illnesses': patient.chronic_illness or 'None recorded',
            'recent_visits': visits_summary,
            'medications': medications_str,
            'lab_results': labs_str,
        }
        
        result = ai_summarize_medical_history(patient_data, user=request.user)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def api_referral_letter(request):
    try:
        data = json.loads(request.body)
        
        patient_id = data.get('patient_id')
        if not patient_id:
            return JsonResponse({'success': False, 'error': 'Patient ID is required'}, status=400)
        
        from patients.models import Patient
        patient = get_object_or_404(Patient, id=patient_id)
        
        age = 'Unknown'
        if patient.date_of_birth:
            today = timezone.now().date()
            age = today.year - patient.date_of_birth.year
        
        patient_data = {
            'name': patient.full_name,
            'age': age,
            'id_number': patient.id_number,
        }
        
        referral_data = {
            'referring_doctor': data.get('referring_doctor', request.user.get_full_name() or request.user.username),
            'referred_to': data.get('referred_to', ''),
            'specialty': data.get('specialty', ''),
            'reason': data.get('reason', ''),
            'clinical_notes': data.get('clinical_notes', ''),
            'diagnosis': data.get('diagnosis', ''),
            'treatment': data.get('treatment', ''),
        }
        
        result = ai_draft_referral_letter(patient_data, referral_data, user=request.user)
        return JsonResponse(result)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(['GET', 'POST'])
def api_stock_suggestions(request):
    try:
        from setup_app.models import Medicine
        
        medicines = Medicine.objects.all()
        stock_data = []
        
        for med in medicines:
            stock_data.append({
                'name': med.name,
                'current': med.stock_quantity,
                'min_level': med.minimum_stock,
            })
        
        low_stock = [item for item in stock_data if item['current'] <= item['min_level']]
        
        result = ai_suggest_stock_order(low_stock if low_stock else stock_data[:20], user=request.user)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(['GET', 'POST'])
def api_dashboard_insights(request):
    try:
        from patients.models import Visit, Consultation
        from finance.models import Invoice, Payment
        from setup_app.models import Medicine
        
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        today_visits = Visit.objects.filter(visit_date=today).count()
        
        week_visits = Visit.objects.filter(visit_date__gte=week_ago, visit_date__lte=today).count()
        avg_7day_visits = round(week_visits / 7, 1)
        
        today_revenue = Payment.objects.filter(
            payment_date__date=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        week_revenue = Payment.objects.filter(
            payment_date__date__gte=week_ago,
            payment_date__date__lte=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        avg_7day_revenue = round(float(week_revenue) / 7, 2)
        
        top_conditions = list(Consultation.objects.filter(
            visit__visit_date__gte=week_ago
        ).exclude(diagnosis='').values_list('diagnosis', flat=True)[:5])
        
        low_stock_count = Medicine.objects.filter(
            stock_quantity__lte=F('minimum_stock')
        ).count()
        
        from patients.models import Appointment
        pending_appointments = Appointment.objects.filter(
            status='scheduled',
            appointment_date__gte=today
        ).count()
        
        clinic_data = {
            'today_visits': today_visits,
            'avg_7day_visits': avg_7day_visits,
            'today_revenue': float(today_revenue),
            'avg_7day_revenue': avg_7day_revenue,
            'top_conditions': top_conditions,
            'top_medicines': [],
            'pending_appointments': pending_appointments,
            'low_stock_count': low_stock_count,
        }
        
        result = ai_generate_dashboard_insights(clinic_data, user=request.user)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def api_assistant(request):
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        context = data.get('context', '')
        
        if not message:
            return JsonResponse({'success': False, 'error': 'Message is required'}, status=400)
        
        message_lower = message.lower()
        
        data_response = _handle_data_query(message_lower, request.user)
        if data_response:
            return JsonResponse({'success': True, 'response': data_response})
        
        result = ai_chat_assistant(message, context, user=request.user)
        return JsonResponse(result)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def _handle_data_query(message: str, user) -> str:
    """Handle data queries and return formatted data instead of guidance."""
    from patients.models import Patient, Visit, Appointment, Consultation
    from finance.models import Invoice, Payment
    from setup_app.models import Medicine
    
    today = timezone.now().date()
    
    if any(kw in message for kw in ['upcoming appointment', 'appointment', 'scheduled']):
        appointments = Appointment.objects.filter(
            status='scheduled',
            appointment_date__gte=today
        ).select_related('patient', 'doctor').order_by('appointment_date', 'appointment_time')[:10]
        
        if not appointments:
            return "No upcoming appointments found."
        
        lines = ["Upcoming Appointments:"]
        for apt in appointments:
            date_str = apt.appointment_date.strftime('%d %b %Y')
            time_str = apt.appointment_time.strftime('%H:%M') if apt.appointment_time else 'No time'
            doctor = apt.doctor.get_full_name() if apt.doctor else 'Not assigned'
            lines.append(f"- {apt.patient.full_name} | {date_str} {time_str} | Dr. {doctor}")
        return "\n".join(lines)
    
    if any(kw in message for kw in ['today visit', "today's visit", 'visit today', 'patient today']):
        visits = Visit.objects.filter(visit_date=today).select_related('patient').order_by('-created_at')[:15]
        
        if not visits:
            return "No visits recorded for today."
        
        lines = [f"Today's Visits ({len(visits)} total):"]
        for v in visits:
            status = v.status.replace('_', ' ').title()
            lines.append(f"- {v.patient.full_name} | {v.visit_type} | {status}")
        return "\n".join(lines)
    
    if any(kw in message for kw in ['pending payment', 'unpaid', 'outstanding']):
        invoices = Invoice.objects.filter(
            status__in=['draft', 'finalized']
        ).filter(balance__gt=0).select_related('patient').order_by('-created_at')[:10]
        
        if not invoices:
            return "No pending payments found."
        
        lines = ["Pending Payments:"]
        for inv in invoices:
            lines.append(f"- {inv.patient.full_name} | RM {inv.balance:.2f} | {inv.invoice_number}")
        return "\n".join(lines)
    
    if any(kw in message for kw in ['low stock', 'stock alert', 'reorder']):
        from django.db.models import F
        low_stock = Medicine.objects.filter(
            stock_quantity__lte=F('minimum_stock'),
            is_active=True
        ).order_by('stock_quantity')[:10]
        
        if not low_stock:
            return "No low stock items at the moment."
        
        lines = ["Low Stock Items:"]
        for med in low_stock:
            lines.append(f"- {med.name} | Stock: {med.stock_quantity} | Min: {med.minimum_stock}")
        return "\n".join(lines)
    
    if any(kw in message for kw in ['today revenue', "today's revenue", 'revenue today', 'today earning', 'today income']):
        total = Payment.objects.filter(
            payment_date__date=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        payments = Payment.objects.filter(payment_date__date=today).count()
        return f"Today's Revenue: RM {total:.2f} from {payments} payment(s)"
    
    if any(kw in message for kw in ['queue', 'waiting']):
        waiting = Visit.objects.filter(
            visit_date=today,
            status__in=['registered', 'triage', 'waiting_doctor']
        ).select_related('patient').order_by('queue_number')[:10]
        
        if not waiting:
            return "No patients currently in queue."
        
        lines = ["Current Queue:"]
        for v in waiting:
            q_num = v.queue_number or '-'
            status = v.status.replace('_', ' ').title()
            lines.append(f"- Q{q_num}: {v.patient.full_name} | {status}")
        return "\n".join(lines)
    
    if any(kw in message for kw in ['patient count', 'total patient', 'how many patient']):
        total = Patient.objects.count()
        today_new = Patient.objects.filter(created_at__date=today).count()
        return f"Total Patients: {total}\nNew Today: {today_new}"
    
    if any(kw in message for kw in ['search patient', 'find patient', 'patient named', 'patient name']):
        import re
        name_match = re.search(r'(?:named?|name|find|search)\s+(.+)', message, re.IGNORECASE)
        if name_match:
            search_term = name_match.group(1).strip()
            patients = Patient.objects.filter(
                full_name__icontains=search_term
            )[:5]
            
            if not patients:
                return f"No patients found matching '{search_term}'"
            
            lines = [f"Patients matching '{search_term}':"]
            for p in patients:
                ic = p.id_number or 'N/A'
                lines.append(f"- {p.full_name} | IC: {ic} | ID: {p.id}")
            return "\n".join(lines)
    
    return None


@login_required
@require_http_methods(['GET', 'POST'])
def api_revenue_forecast(request):
    try:
        from finance.models import Payment
        from patients.models import Visit
        
        today = timezone.now().date()
        start_date = today - timedelta(days=30)
        
        historical_data = []
        current_date = start_date
        
        while current_date <= today:
            day_visits = Visit.objects.filter(visit_date=current_date).count()
            day_revenue = Payment.objects.filter(
                payment_date__date=current_date
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            historical_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'visits': day_visits,
                'revenue': float(day_revenue),
            })
            current_date += timedelta(days=1)
        
        days = int(request.GET.get('days', 7))
        result = ai_forecast_revenue(historical_data, days, user=request.user)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(['GET', 'POST'])
def api_anomaly_detection(request):
    try:
        from finance.models import Payment, Invoice
        
        today = timezone.now().date()
        start_date = today - timedelta(days=30)
        
        payments = Payment.objects.filter(
            payment_date__date__gte=start_date
        ).select_related('invoice', 'collected_by').order_by('-payment_date')[:50]
        
        transaction_data = []
        for p in payments:
            transaction_data.append({
                'date': p.payment_date.strftime('%Y-%m-%d %H:%M'),
                'type': f'Payment ({p.payment_method})',
                'amount': float(p.amount),
                'user': p.collected_by.username if p.collected_by else 'Unknown',
            })
        
        result = ai_detect_anomalies(transaction_data, user=request.user)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def api_prescription_suggestions(request, consultation_id):
    try:
        from patients.models import Consultation, Prescription
        from setup_app.models import Medicine
        import uuid
        
        consultation = get_object_or_404(Consultation, id=consultation_id)
        patient = consultation.visit.patient
        
        allergies = ', '.join([a.name for a in patient.allergies.all()]) if patient.allergies.exists() else 'None known'
        
        consultation_data = {
            'patient_age': patient.age,
            'patient_gender': patient.get_gender_display() if hasattr(patient, 'get_gender_display') else patient.gender,
            'allergies': allergies,
            'chief_complaint': consultation.chief_complaint,
            'diagnosis': consultation.diagnosis,
            'treatment_plan': consultation.treatment_plan or '',
            'bp': consultation.vitals_bp or '-',
            'pulse': consultation.vitals_pulse or '-',
        }
        
        available_medicines = list(Medicine.objects.filter(is_active=True).values(
            'id', 'name', 'generic_name', 'strength', 'form', 'selling_price'
        ))
        
        result = ai_suggest_prescriptions(consultation_data, available_medicines, user=request.user)
        
        if result.get('success') and result.get('prescriptions'):
            for rx in result['prescriptions']:
                medicine_name = rx.get('medicine_name', '').strip()
                if not medicine_name:
                    continue
                    
                med = Medicine.objects.filter(name__iexact=medicine_name).first()
                if not med:
                    med = Medicine.objects.filter(name__icontains=medicine_name).first()
                
                if med:
                    rx['medicine_id'] = med.id
                    rx['medicine_name'] = med.name
                    rx['is_new_medicine'] = False
                else:
                    sku = f"AI-{uuid.uuid4().hex[:8].upper()}"
                    form_type = rx.get('form', 'tablet').lower() if rx.get('form') else 'tablet'
                    if form_type not in ['tablet', 'capsule', 'syrup', 'injection', 'cream', 'ointment', 'drops', 'inhaler', 'suppository', 'patch']:
                        form_type = 'tablet'
                    
                    new_med = Medicine.objects.create(
                        name=medicine_name,
                        generic_name=rx.get('generic_name', ''),
                        strength=rx.get('dosage', ''),
                        form=form_type,
                        sku=sku,
                        selling_price=0,
                        cost_price=0,
                        stock_quantity=100,
                        minimum_stock=10,
                        is_active=True,
                    )
                    rx['medicine_id'] = new_med.id
                    rx['is_new_medicine'] = True
                    rx['auto_added'] = True
        
        return JsonResponse(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
