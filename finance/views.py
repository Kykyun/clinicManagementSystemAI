from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, timedelta
import uuid
from .models import Invoice, InvoiceItem, Payment, Supplier, StockOrder, StockOrderItem, PanelClaim, EODReport
from .forms import InvoiceForm, InvoiceItemForm, PaymentForm, SupplierForm, StockOrderForm, StockOrderItemForm, PanelClaimForm
from patients.models import Visit, Consultation, Prescription
from setup_app.models import Panel, Fee
from accounts.decorators import finance_access_required, admin_or_hq_required
from einvoice.models import EInvoiceDocument


def generate_invoice_number():
    return f"INV{timezone.now().strftime('%Y%m%d%H%M%S')}"


def generate_order_number():
    return f"PO{timezone.now().strftime('%Y%m%d%H%M%S')}"


def generate_claim_number():
    return f"CLM{timezone.now().strftime('%Y%m%d%H%M%S')}"


@login_required
@finance_access_required
def invoice_list(request):
    status_filter = request.GET.get('status', '')
    invoices = Invoice.objects.all()
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    return render(request, 'finance/invoice_list.html', {'invoices': invoices, 'status_filter': status_filter})


@login_required
@finance_access_required
def invoice_create(request, visit_id=None):
    initial = {}
    visit = None
    if visit_id:
        visit = get_object_or_404(Visit, pk=visit_id)
        initial['visit'] = visit
        initial['patient'] = visit.patient
        if visit.patient.panel:
            initial['panel'] = visit.patient.panel
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.invoice_number = generate_invoice_number()
            invoice.created_by = request.user
            invoice.save()
            messages.success(request, f'Invoice {invoice.invoice_number} created.')
            return redirect('finance:invoice_items', pk=invoice.pk)
    else:
        form = InvoiceForm(initial=initial)
    return render(request, 'finance/invoice_form.html', {'form': form, 'title': 'Create Invoice', 'visit': visit})


@login_required
@finance_access_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    items = invoice.items.all()
    payments = invoice.payments.all()
    return render(request, 'finance/invoice_detail.html', {'invoice': invoice, 'items': items, 'payments': payments})


@login_required
@finance_access_required
def invoice_items(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        form = InvoiceItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.invoice = invoice
            item.save()
            invoice.subtotal = sum(i.total for i in invoice.items.all())
            invoice.total_amount = invoice.subtotal + invoice.tax_amount - invoice.discount
            invoice.outstanding_balance = invoice.total_amount - invoice.amount_paid
            invoice.save()
            messages.success(request, 'Item added to invoice.')
            return redirect('finance:invoice_items', pk=pk)
    else:
        form = InvoiceItemForm()
    items = invoice.items.all()
    return render(request, 'finance/invoice_items.html', {'invoice': invoice, 'items': items, 'form': form})


@login_required
@finance_access_required
def invoice_finalize(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    invoice.subtotal = sum(i.total for i in invoice.items.all())
    invoice.total_amount = invoice.subtotal + invoice.tax_amount - invoice.discount
    invoice.outstanding_balance = invoice.total_amount - invoice.amount_paid
    invoice.save()
    messages.success(request, 'Invoice finalized.')
    return redirect('finance:invoice_detail', pk=pk)


@login_required
@finance_access_required
def payment_create(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.received_by = request.user
            payment.save()
            messages.success(request, f'Payment of RM {payment.amount} recorded.')
            return redirect('finance:invoice_detail', pk=invoice.pk)
    else:
        form = PaymentForm(initial={'amount': invoice.outstanding_balance})
    return render(request, 'finance/payment_form.html', {'form': form, 'invoice': invoice})


@login_required
@finance_access_required
def supplier_list(request):
    suppliers = Supplier.objects.filter(is_active=True)
    return render(request, 'finance/supplier_list.html', {'suppliers': suppliers})


@login_required
@finance_access_required
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier added successfully.')
            return redirect('finance:supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'finance/supplier_form.html', {'form': form, 'title': 'Add Supplier'})


@login_required
@finance_access_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier updated successfully.')
            return redirect('finance:supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'finance/supplier_form.html', {'form': form, 'title': 'Edit Supplier'})


@login_required
@finance_access_required
def stock_order_list(request):
    orders = StockOrder.objects.all().order_by('-order_date')
    return render(request, 'finance/stock_order_list.html', {'orders': orders})


@login_required
@finance_access_required
def stock_order_create(request):
    if request.method == 'POST':
        form = StockOrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.order_number = generate_order_number()
            order.created_by = request.user
            order.save()
            messages.success(request, f'Order {order.order_number} created.')
            return redirect('finance:stock_order_items', pk=order.pk)
    else:
        form = StockOrderForm(initial={'order_date': timezone.now().date()})
    return render(request, 'finance/stock_order_form.html', {'form': form, 'title': 'Create Stock Order'})


@login_required
@finance_access_required
def stock_order_items(request, pk):
    order = get_object_or_404(StockOrder, pk=pk)
    if request.method == 'POST':
        form = StockOrderItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.order = order
            item.save()
            order.total_amount = sum(i.total for i in order.items.all())
            order.save()
            messages.success(request, 'Item added to order.')
            return redirect('finance:stock_order_items', pk=pk)
    else:
        form = StockOrderItemForm()
    items = order.items.all()
    return render(request, 'finance/stock_order_items.html', {'order': order, 'items': items, 'form': form})


@login_required
@finance_access_required
def stock_order_status(request, pk, status):
    order = get_object_or_404(StockOrder, pk=pk)
    if status in ['ordered', 'shipped', 'delivered', 'cancelled']:
        order.status = status
        if status == 'delivered':
            order.actual_delivery = timezone.now().date()
            for item in order.items.all():
                if item.medicine:
                    item.medicine.stock_quantity += item.quantity
                    item.medicine.save()
                elif item.disposable:
                    item.disposable.stock_quantity += item.quantity
                    item.disposable.save()
        order.save()
        messages.success(request, f'Order marked as {status}.')
    return redirect('finance:stock_order_list')


@login_required
@finance_access_required
def panel_claim_list(request):
    claims = PanelClaim.objects.all().order_by('-created_at')
    return render(request, 'finance/panel_claim_list.html', {'claims': claims})


@login_required
@finance_access_required
def panel_claim_create(request):
    if request.method == 'POST':
        form = PanelClaimForm(request.POST)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.claim_number = generate_claim_number()
            claim.created_by = request.user
            claim.save()
            messages.success(request, f'Claim {claim.claim_number} created.')
            return redirect('finance:panel_claim_list')
    else:
        form = PanelClaimForm()
    return render(request, 'finance/panel_claim_form.html', {'form': form, 'title': 'Create Panel Claim'})


@login_required
@finance_access_required
def eod_report(request):
    report_date = request.GET.get('date', timezone.now().date().isoformat())
    
    try:
        report = EODReport.objects.get(report_date=report_date)
    except EODReport.DoesNotExist:
        payments = Payment.objects.filter(payment_date__date=report_date)
        report = EODReport(
            report_date=report_date,
            total_patients=Visit.objects.filter(visit_date__date=report_date).count(),
            total_cash=payments.filter(payment_method='cash').aggregate(Sum('amount'))['amount__sum'] or 0,
            total_card=payments.filter(payment_method='card').aggregate(Sum('amount'))['amount__sum'] or 0,
            total_ewallet=payments.filter(payment_method='ewallet').aggregate(Sum('amount'))['amount__sum'] or 0,
            total_credit=payments.filter(payment_method='credit').aggregate(Sum('amount'))['amount__sum'] or 0,
        )
        report.total_revenue = report.total_cash + report.total_card + report.total_ewallet + report.total_credit
    
    einvoice_stats = EInvoiceDocument.objects.filter(
        created_at__date=report_date
    ).aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        submitted=Count('id', filter=Q(status='submitted')),
        valid=Count('id', filter=Q(status='valid')),
        invalid=Count('id', filter=Q(status='invalid')),
        rejected=Count('id', filter=Q(status='rejected')),
        cancelled=Count('id', filter=Q(status='cancelled')),
        total_amount=Sum('total_amount', filter=Q(status='valid'))
    )
    
    return render(request, 'finance/eod_report.html', {
        'report': report,
        'report_date': report_date,
        'einvoice_stats': einvoice_stats,
    })


@login_required
@finance_access_required
def eod_generate(request):
    report_date = request.POST.get('date', timezone.now().date().isoformat())
    payments = Payment.objects.filter(payment_date__date=report_date)
    
    report, created = EODReport.objects.update_or_create(
        report_date=report_date,
        defaults={
            'total_patients': Visit.objects.filter(visit_date__date=report_date).count(),
            'total_cash': payments.filter(payment_method='cash').aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_card': payments.filter(payment_method='card').aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_ewallet': payments.filter(payment_method='ewallet').aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_credit': payments.filter(payment_method='credit').aggregate(Sum('amount'))['amount__sum'] or 0,
            'generated_by': request.user,
        }
    )
    report.total_revenue = report.total_cash + report.total_card + report.total_ewallet + report.total_credit
    report.save()
    
    messages.success(request, f'EOD Report generated for {report_date}.')
    return redirect('finance:eod_report')


@login_required
@finance_access_required
def credit_payment_list(request):
    invoices = Invoice.objects.filter(status__in=['pending', 'partial']).order_by('-invoice_date')
    return render(request, 'finance/credit_payment_list.html', {'invoices': invoices})


@login_required
@finance_access_required
def billing_dashboard(request):
    visits_ready = Visit.objects.filter(status='ready_for_payment').select_related('patient').order_by('visit_date')
    today = timezone.now().date()
    today_invoices = Invoice.objects.filter(invoice_date__date=today)
    today_payments = Payment.objects.filter(payment_date__date=today)
    
    stats = {
        'pending_count': visits_ready.count(),
        'invoices_today': today_invoices.count(),
        'revenue_today': today_payments.aggregate(total=Sum('amount'))['total'] or 0,
        'pending_invoices': Invoice.objects.filter(status__in=['pending', 'partial']).count(),
    }
    
    return render(request, 'finance/billing_dashboard.html', {
        'visits': visits_ready,
        'stats': stats,
    })


@login_required
@finance_access_required
def quick_invoice_create(request, visit_id):
    visit = get_object_or_404(Visit, pk=visit_id)
    
    existing_invoice = Invoice.objects.filter(visit=visit).first()
    if existing_invoice:
        messages.info(request, 'Invoice already exists for this visit.')
        return redirect('finance:invoice_detail', pk=existing_invoice.pk)
    
    invoice = Invoice.objects.create(
        invoice_number=generate_invoice_number(),
        patient=visit.patient,
        visit=visit,
        panel=visit.patient.panel if visit.patient.panel else None,
        created_by=request.user,
    )
    
    try:
        consultation = visit.consultation
        consultation_fee = Fee.objects.filter(name__icontains='consultation').first()
        if consultation_fee:
            InvoiceItem.objects.create(
                invoice=invoice,
                item_type='consultation',
                description=f'Consultation - {consultation_fee.name}',
                quantity=1,
                unit_price=consultation_fee.amount,
                total=consultation_fee.amount,
            )
        
        prescriptions = Prescription.objects.filter(consultation=consultation)
        for rx in prescriptions:
            if rx.medicine:
                item_total = rx.medicine.selling_price * rx.quantity
                InvoiceItem.objects.create(
                    invoice=invoice,
                    item_type='medicine',
                    description=f'{rx.medicine.name} x{rx.quantity}',
                    quantity=rx.quantity,
                    unit_price=rx.medicine.selling_price,
                    total=item_total,
                )
    except Exception:
        pass
    
    invoice.subtotal = sum(i.total for i in invoice.items.all())
    invoice.total_amount = invoice.subtotal + invoice.tax_amount - invoice.discount
    invoice.outstanding_balance = invoice.total_amount - invoice.amount_paid
    invoice.save()
    
    messages.success(request, f'Invoice {invoice.invoice_number} created with items from visit.')
    return redirect('finance:invoice_items', pk=invoice.pk)


@login_required
@finance_access_required
def complete_billing(request, visit_id):
    visit = get_object_or_404(Visit, pk=visit_id)
    visit.status = 'completed'
    visit.save()
    messages.success(request, f'Visit for {visit.patient.full_name} marked as completed.')
    return redirect('finance:billing_dashboard')
