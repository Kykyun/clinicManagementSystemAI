from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum

from accounts.decorators import admin_or_hq_required, finance_access_required
from finance.models import Invoice, PanelClaim
from .models import EInvoiceConfig, EInvoiceDocument, EInvoiceLog, TINValidation
from .forms import EInvoiceConfigForm, CancelEInvoiceForm, ValidateTINForm
from .services import MyInvoisService, create_einvoice_from_invoice, create_einvoice_from_panel_claim


@login_required
@finance_access_required
def einvoice_list(request):
    documents = EInvoiceDocument.objects.select_related('invoice', 'panel_claim', 'created_by')

    status_filter = request.GET.get('status', '')
    if status_filter:
        documents = documents.filter(status=status_filter)

    search = request.GET.get('search', '')
    if search:
        documents = documents.filter(
            Q(internal_id__icontains=search) |
            Q(buyer_name__icontains=search) |
            Q(buyer_tin__icontains=search) |
            Q(myinvois_uuid__icontains=search)
        )

    config = EInvoiceConfig.get_config()

    stats = EInvoiceDocument.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        submitted=Count('id', filter=Q(status='submitted')),
        valid=Count('id', filter=Q(status='valid')),
        invalid=Count('id', filter=Q(status='invalid')),
        rejected=Count('id', filter=Q(status='rejected')),
        cancelled=Count('id', filter=Q(status='cancelled')),
        total_amount=Sum('total_amount', filter=Q(status='valid'))
    )

    paginator = Paginator(documents, 20)
    page = request.GET.get('page', 1)
    documents = paginator.get_page(page)

    context = {
        'documents': documents,
        'config': config,
        'stats': stats,
        'status_filter': status_filter,
        'search': search,
        'status_choices': EInvoiceDocument.STATUS_CHOICES,
    }
    return render(request, 'einvoice/list.html', context)


@login_required
@admin_or_hq_required
def einvoice_config(request):
    config = EInvoiceConfig.get_config()

    if request.method == 'POST':
        form = EInvoiceConfigForm(request.POST, instance=config)
        if form.is_valid():
            config = form.save(commit=False)
            config.updated_by = request.user
            config.save()
            messages.success(request, 'E-Invoice configuration updated successfully.')
            return redirect('einvoice:config')
    else:
        form = EInvoiceConfigForm(instance=config)

    context = {
        'form': form,
        'config': config,
    }
    return render(request, 'einvoice/config.html', context)


@login_required
@finance_access_required
def einvoice_detail(request, pk):
    document = get_object_or_404(EInvoiceDocument, pk=pk)
    logs = document.logs.all()[:20]
    config = EInvoiceConfig.get_config()

    context = {
        'document': document,
        'logs': logs,
        'config': config,
    }
    return render(request, 'einvoice/detail.html', context)


@login_required
@finance_access_required
def submit_einvoice(request, pk):
    document = get_object_or_404(EInvoiceDocument, pk=pk)

    if not document.can_resubmit:
        messages.error(request, f'Document cannot be submitted in {document.get_status_display()} status.')
        return redirect('einvoice:detail', pk=pk)

    service = MyInvoisService()
    success, message, response = service.submit_document(document, user=request.user)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, f'Submission failed: {message}')

    return redirect('einvoice:detail', pk=pk)


@login_required
@finance_access_required
def check_status(request, pk):
    document = get_object_or_404(EInvoiceDocument, pk=pk)

    if not document.myinvois_uuid:
        messages.error(request, 'Document has not been submitted yet.')
        return redirect('einvoice:detail', pk=pk)

    service = MyInvoisService()
    success, message, response = service.get_document_status(document, user=request.user)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, f'Status check failed: {message}')

    return redirect('einvoice:detail', pk=pk)


@login_required
@finance_access_required
def cancel_einvoice(request, pk):
    document = get_object_or_404(EInvoiceDocument, pk=pk)

    if not document.can_cancel:
        messages.error(request, f'Document cannot be cancelled in {document.get_status_display()} status.')
        return redirect('einvoice:detail', pk=pk)

    if request.method == 'POST':
        form = CancelEInvoiceForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['reason']
            service = MyInvoisService()
            success, message, response = service.cancel_document(document, reason, user=request.user)

            if success:
                messages.success(request, message)
            else:
                messages.error(request, f'Cancellation failed: {message}')

            return redirect('einvoice:detail', pk=pk)
    else:
        form = CancelEInvoiceForm()

    context = {
        'document': document,
        'form': form,
    }
    return render(request, 'einvoice/cancel.html', context)


@login_required
@finance_access_required
def view_payload(request, pk):
    document = get_object_or_404(EInvoiceDocument, pk=pk)

    context = {
        'document': document,
    }
    return render(request, 'einvoice/payload.html', context)


@login_required
@finance_access_required
def create_from_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    existing = EInvoiceDocument.objects.filter(
        invoice=invoice,
        status__in=['pending', 'submitted', 'valid']
    ).first()

    if existing:
        messages.info(request, 'An e-invoice document already exists for this invoice.')
        return redirect('einvoice:detail', pk=existing.pk)

    document = create_einvoice_from_invoice(invoice, user=request.user)
    messages.success(request, f'E-invoice document created: {document.internal_id}')
    return redirect('einvoice:detail', pk=document.pk)


@login_required
@finance_access_required
def create_from_claim(request, claim_id):
    claim = get_object_or_404(PanelClaim, pk=claim_id)

    existing = EInvoiceDocument.objects.filter(
        panel_claim=claim,
        status__in=['pending', 'submitted', 'valid']
    ).first()

    if existing:
        messages.info(request, 'An e-invoice document already exists for this claim.')
        return redirect('einvoice:detail', pk=existing.pk)

    document = create_einvoice_from_panel_claim(claim, user=request.user)
    messages.success(request, f'E-invoice document created: {document.internal_id}')
    return redirect('einvoice:detail', pk=document.pk)


@login_required
@finance_access_required
def validate_tin(request):
    config = EInvoiceConfig.get_config()
    result = None
    form = ValidateTINForm()

    if request.method == 'POST':
        form = ValidateTINForm(request.POST)
        if form.is_valid():
            tin = form.cleaned_data['tin']
            id_type = form.cleaned_data['id_type']
            id_value = form.cleaned_data.get('id_value', '')

            service = MyInvoisService()
            success, message, response = service.validate_tin(tin, id_type, id_value, user=request.user)

            result = {
                'success': success,
                'message': message,
                'tin': tin,
                'taxpayer_name': response.get('name', '') if success else '',
            }

    validations = TINValidation.objects.all()[:20]

    context = {
        'form': form,
        'result': result,
        'validations': validations,
        'config': config,
    }
    return render(request, 'einvoice/validate_tin.html', context)


@login_required
@admin_or_hq_required
def test_authentication(request):
    config = EInvoiceConfig.get_config()

    if request.method == 'POST':
        service = MyInvoisService()
        success, message = service.authenticate(user=request.user)

        if success:
            messages.success(request, message)
        else:
            messages.error(request, f'Authentication failed: {message}')

    return redirect('einvoice:config')


@login_required
@finance_access_required
def einvoice_logs(request):
    logs = EInvoiceLog.objects.select_related('document', 'created_by').all()

    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)

    paginator = Paginator(logs, 50)
    page = request.GET.get('page', 1)
    logs = paginator.get_page(page)

    context = {
        'logs': logs,
        'action_filter': action_filter,
        'action_choices': EInvoiceLog.ACTION_CHOICES,
    }
    return render(request, 'einvoice/logs.html', context)


@login_required
@finance_access_required
def batch_submit(request):
    if request.method == 'POST':
        document_ids = request.POST.getlist('document_ids')
        if not document_ids:
            messages.error(request, 'No documents selected.')
            return redirect('einvoice:list')

        documents = EInvoiceDocument.objects.filter(pk__in=document_ids, status='pending')
        service = MyInvoisService()

        success_count = 0
        error_count = 0

        for doc in documents:
            success, message, _ = service.submit_document(doc, user=request.user)
            if success:
                success_count += 1
            else:
                error_count += 1

        messages.success(request, f'Batch submission complete. Success: {success_count}, Failed: {error_count}')
        return redirect('einvoice:list')

    documents = EInvoiceDocument.objects.filter(status='pending')
    context = {
        'documents': documents,
    }
    return render(request, 'einvoice/batch_submit.html', context)


@login_required
@finance_access_required
def sync_all_status(request):
    if request.method == 'POST':
        documents = EInvoiceDocument.objects.filter(status='submitted').exclude(myinvois_uuid='')
        service = MyInvoisService()

        updated_count = 0
        for doc in documents:
            success, _, _ = service.get_document_status(doc, user=request.user)
            if success:
                updated_count += 1

        messages.success(request, f'Status sync complete. Updated {updated_count} documents.')

    return redirect('einvoice:list')
