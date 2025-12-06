from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import datetime, timedelta
import csv
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from .models import ClinicSettings, Attendance, QueueTicket, PromotionalProduct, MembershipReward
from .forms import ClinicSettingsForm, AttendanceForm, QueueTicketForm, PromotionalProductForm
from patients.models import Patient, Visit, Appointment
from finance.models import Invoice, Payment
from setup_app.models import Medicine
from accounts.models import User


@login_required
def dashboard(request):
    today = timezone.now().date()
    
    context = {
        'total_patients_today': Visit.objects.filter(visit_date__date=today).count(),
        'total_appointments_today': Appointment.objects.filter(appointment_date=today).count(),
        'pending_appointments': Appointment.objects.filter(appointment_date=today, status='scheduled').count(),
        'completed_visits': Visit.objects.filter(visit_date__date=today, status='completed').count(),
        'revenue_today': Payment.objects.filter(payment_date__date=today).aggregate(Sum('amount'))['amount__sum'] or 0,
        'pending_invoices': Invoice.objects.filter(status__in=['pending', 'partial']).count(),
        'low_stock_medicines': Medicine.objects.filter(stock_quantity__lte=models.F('minimum_stock')).count(),
        'recent_visits': Visit.objects.all()[:5],
        'recent_patients': Patient.objects.all()[:5],
        'upcoming_appointments': Appointment.objects.filter(
            appointment_date__gte=today,
            status='scheduled'
        ).order_by('appointment_date', 'appointment_time')[:5],
    }
    return render(request, 'management/dashboard.html', context)


@login_required
def clinic_settings(request):
    if request.user.role not in ['admin']:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('management_app:dashboard')
    
    settings_obj, created = ClinicSettings.objects.get_or_create(pk=1, defaults={
        'clinic_name': 'My Clinic',
        'address': '',
        'phone': '',
    })
    
    if request.method == 'POST':
        form = ClinicSettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clinic settings updated successfully.')
            return redirect('management_app:clinic_settings')
    else:
        form = ClinicSettingsForm(instance=settings_obj)
    return render(request, 'management/clinic_settings.html', {'form': form})


@login_required
def attendance_list(request):
    date_filter = request.GET.get('date', timezone.now().date().isoformat())
    attendance = Attendance.objects.filter(date=date_filter)
    staff = User.objects.filter(is_active_staff=True)
    return render(request, 'management/attendance_list.html', {
        'attendance': attendance,
        'date_filter': date_filter,
        'staff': staff
    })


@login_required
def attendance_checkin(request):
    today = timezone.now().date()
    attendance, created = Attendance.objects.get_or_create(
        staff=request.user,
        date=today,
        defaults={'check_in': timezone.now().time(), 'status': 'present'}
    )
    if not created and not attendance.check_in:
        attendance.check_in = timezone.now().time()
        attendance.status = 'present'
        attendance.save()
    messages.success(request, 'Check-in recorded.')
    return redirect('management_app:dashboard')


@login_required
def attendance_checkout(request):
    today = timezone.now().date()
    try:
        attendance = Attendance.objects.get(staff=request.user, date=today)
        attendance.check_out = timezone.now().time()
        attendance.save()
        messages.success(request, 'Check-out recorded.')
    except Attendance.DoesNotExist:
        messages.error(request, 'No check-in found for today.')
    return redirect('management_app:dashboard')


@login_required
def queue_display(request):
    today = timezone.now().date()
    queue = QueueTicket.objects.filter(date=today).order_by('ticket_number')
    waiting = queue.filter(status='waiting')
    current = queue.filter(status__in=['called', 'in_service']).first()
    return render(request, 'management/queue_display.html', {
        'queue': queue,
        'waiting': waiting,
        'current': current
    })


@login_required
def queue_ticket_create(request):
    today = timezone.now().date()
    if request.method == 'POST':
        form = QueueTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.date = today
            last_ticket = QueueTicket.objects.filter(date=today).order_by('-ticket_number').first()
            ticket.ticket_number = (last_ticket.ticket_number + 1) if last_ticket else 1
            ticket.save()
            messages.success(request, f'Queue ticket #{ticket.ticket_number} created.')
            return redirect('management_app:queue_display')
    else:
        form = QueueTicketForm()
        form.fields['doctor'].queryset = User.objects.filter(role='doctor', is_active=True)
    return render(request, 'management/queue_ticket_form.html', {'form': form})


@login_required
def queue_call_next(request):
    today = timezone.now().date()
    current = QueueTicket.objects.filter(date=today, status__in=['called', 'in_service']).first()
    if current:
        current.status = 'completed'
        current.save()
    
    next_ticket = QueueTicket.objects.filter(date=today, status='waiting').order_by('ticket_number').first()
    if next_ticket:
        next_ticket.status = 'called'
        next_ticket.called_at = timezone.now()
        next_ticket.save()
        messages.success(request, f'Calling ticket #{next_ticket.ticket_number}')
    else:
        messages.info(request, 'No more patients in queue.')
    return redirect('management_app:queue_display')


@login_required
def reporting(request):
    report_type = request.GET.get('type', 'daily')
    start_date = request.GET.get('start', (timezone.now() - timedelta(days=30)).date().isoformat())
    end_date = request.GET.get('end', timezone.now().date().isoformat())
    
    visits = Visit.objects.filter(visit_date__date__gte=start_date, visit_date__date__lte=end_date)
    payments = Payment.objects.filter(payment_date__date__gte=start_date, payment_date__date__lte=end_date)
    
    context = {
        'report_type': report_type,
        'start_date': start_date,
        'end_date': end_date,
        'total_visits': visits.count(),
        'total_revenue': payments.aggregate(Sum('amount'))['amount__sum'] or 0,
        'revenue_by_method': payments.values('payment_method').annotate(total=Sum('amount')),
        'visits_by_type': visits.values('visit_type').annotate(count=Count('id')),
        'top_medicines': Medicine.objects.filter(
            prescription__consultation__visit__visit_date__date__gte=start_date
        ).annotate(
            count=Count('prescription')
        ).order_by('-count')[:10],
    }
    return render(request, 'management/reporting.html', context)


@login_required
def export_report_csv(request):
    start_date = request.GET.get('start', (timezone.now() - timedelta(days=30)).date().isoformat())
    end_date = request.GET.get('end', timezone.now().date().isoformat())
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="report_{start_date}_to_{end_date}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Patient', 'Visit Type', 'Doctor', 'Amount'])
    
    visits = Visit.objects.filter(visit_date__date__gte=start_date, visit_date__date__lte=end_date)
    for visit in visits:
        invoice = Invoice.objects.filter(visit=visit).first()
        writer.writerow([
            visit.visit_date.date(),
            visit.patient.full_name,
            visit.get_visit_type_display(),
            visit.doctor.get_full_name() if visit.doctor else 'N/A',
            invoice.total_amount if invoice else 0
        ])
    
    return response


@login_required
def export_report_pdf(request):
    start_date = request.GET.get('start', (timezone.now() - timedelta(days=30)).date().isoformat())
    end_date = request.GET.get('end', timezone.now().date().isoformat())
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, "Clinic Report")
    p.setFont("Helvetica", 12)
    p.drawString(100, 730, f"Period: {start_date} to {end_date}")
    
    visits = Visit.objects.filter(visit_date__date__gte=start_date, visit_date__date__lte=end_date)
    payments = Payment.objects.filter(payment_date__date__gte=start_date, payment_date__date__lte=end_date)
    
    y = 700
    p.drawString(100, y, f"Total Visits: {visits.count()}")
    y -= 20
    p.drawString(100, y, f"Total Revenue: ${payments.aggregate(Sum('amount'))['amount__sum'] or 0:.2f}")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="report_{start_date}_to_{end_date}.pdf"'
    return response


@login_required
def promotional_list(request):
    products = PromotionalProduct.objects.all()
    return render(request, 'management/promotional_list.html', {'products': products})


@login_required
def promotional_create(request):
    if request.method == 'POST':
        form = PromotionalProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Promotional product added.')
            return redirect('management_app:promotional_list')
    else:
        form = PromotionalProductForm()
    return render(request, 'management/promotional_form.html', {'form': form, 'title': 'Add Promotion'})


@login_required
def dashboard_data(request):
    today = timezone.now().date()
    last_7_days = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    
    visit_data = []
    revenue_data = []
    for date_str in last_7_days:
        visit_data.append(Visit.objects.filter(visit_date__date=date_str).count())
        revenue_data.append(float(Payment.objects.filter(payment_date__date=date_str).aggregate(Sum('amount'))['amount__sum'] or 0))
    
    return JsonResponse({
        'labels': last_7_days,
        'visits': visit_data,
        'revenue': revenue_data
    })


from django.db import models
