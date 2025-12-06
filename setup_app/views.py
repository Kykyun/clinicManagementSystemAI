from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from .models import Medicine, LabTest, Allergy, Disposable, Room, Fee, Panel
from .forms import MedicineForm, LabTestForm, AllergyForm, DisposableForm, RoomForm, FeeForm, PanelForm
from accounts.models import AuditLog
from accounts.decorators import admin_or_hq_required, admin_required


@login_required
def medicine_list(request):
    query = request.GET.get('q', '')
    show_low_stock = request.GET.get('low_stock', '')
    medicines = Medicine.objects.filter(is_active=True)
    
    if query:
        medicines = medicines.filter(
            Q(name__icontains=query) |
            Q(generic_name__icontains=query) |
            Q(sku__icontains=query)
        )
    
    if show_low_stock:
        medicines = medicines.filter(stock_quantity__lte=F('minimum_stock'))
    
    return render(request, 'setup/medicine_list.html', {'medicines': medicines, 'query': query})


@login_required
@admin_or_hq_required
def medicine_create(request):
    if request.method == 'POST':
        form = MedicineForm(request.POST)
        if form.is_valid():
            medicine = form.save()
            AuditLog.objects.create(
                user=request.user,
                action='create',
                model_name='Medicine',
                object_id=str(medicine.id),
                details=f'Created medicine: {medicine.name}'
            )
            messages.success(request, f'Medicine {medicine.name} added successfully.')
            return redirect('setup_app:medicine_list')
    else:
        form = MedicineForm()
    return render(request, 'setup/medicine_form.html', {'form': form, 'title': 'Add Medicine'})


@login_required
@admin_or_hq_required
def medicine_edit(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        form = MedicineForm(request.POST, instance=medicine)
        if form.is_valid():
            form.save()
            AuditLog.objects.create(
                user=request.user,
                action='update',
                model_name='Medicine',
                object_id=str(medicine.id),
                details=f'Updated medicine: {medicine.name}'
            )
            messages.success(request, f'Medicine {medicine.name} updated successfully.')
            return redirect('setup_app:medicine_list')
    else:
        form = MedicineForm(instance=medicine)
    return render(request, 'setup/medicine_form.html', {'form': form, 'title': 'Edit Medicine', 'medicine': medicine})


@login_required
def lab_test_list(request):
    lab_tests = LabTest.objects.filter(is_active=True)
    return render(request, 'setup/lab_test_list.html', {'lab_tests': lab_tests})


@login_required
@admin_or_hq_required
def lab_test_create(request):
    if request.method == 'POST':
        form = LabTestForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lab test added successfully.')
            return redirect('setup_app:lab_test_list')
    else:
        form = LabTestForm()
    return render(request, 'setup/lab_test_form.html', {'form': form, 'title': 'Add Lab Test'})


@login_required
@admin_or_hq_required
def lab_test_edit(request, pk):
    lab_test = get_object_or_404(LabTest, pk=pk)
    if request.method == 'POST':
        form = LabTestForm(request.POST, instance=lab_test)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lab test updated successfully.')
            return redirect('setup_app:lab_test_list')
    else:
        form = LabTestForm(instance=lab_test)
    return render(request, 'setup/lab_test_form.html', {'form': form, 'title': 'Edit Lab Test'})


@login_required
def allergy_list(request):
    allergies = Allergy.objects.filter(is_active=True)
    return render(request, 'setup/allergy_list.html', {'allergies': allergies})


@login_required
@admin_or_hq_required
def allergy_create(request):
    if request.method == 'POST':
        form = AllergyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Allergy added successfully.')
            return redirect('setup_app:allergy_list')
    else:
        form = AllergyForm()
    return render(request, 'setup/allergy_form.html', {'form': form, 'title': 'Add Allergy'})


@login_required
def disposable_list(request):
    disposables = Disposable.objects.filter(is_active=True)
    return render(request, 'setup/disposable_list.html', {'disposables': disposables})


@login_required
@admin_or_hq_required
def disposable_create(request):
    if request.method == 'POST':
        form = DisposableForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Disposable item added successfully.')
            return redirect('setup_app:disposable_list')
    else:
        form = DisposableForm()
    return render(request, 'setup/disposable_form.html', {'form': form, 'title': 'Add Disposable'})


@login_required
@admin_or_hq_required
def disposable_edit(request, pk):
    disposable = get_object_or_404(Disposable, pk=pk)
    if request.method == 'POST':
        form = DisposableForm(request.POST, instance=disposable)
        if form.is_valid():
            form.save()
            messages.success(request, 'Disposable item updated successfully.')
            return redirect('setup_app:disposable_list')
    else:
        form = DisposableForm(instance=disposable)
    return render(request, 'setup/disposable_form.html', {'form': form, 'title': 'Edit Disposable'})


@login_required
def room_list(request):
    rooms = Room.objects.all()
    return render(request, 'setup/room_list.html', {'rooms': rooms})


@login_required
@admin_or_hq_required
def room_create(request):
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Room added successfully.')
            return redirect('setup_app:room_list')
    else:
        form = RoomForm()
    return render(request, 'setup/room_form.html', {'form': form, 'title': 'Add Room'})


@login_required
def fee_list(request):
    fees = Fee.objects.filter(is_active=True)
    return render(request, 'setup/fee_list.html', {'fees': fees})


@login_required
@admin_or_hq_required
def fee_create(request):
    if request.method == 'POST':
        form = FeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fee added successfully.')
            return redirect('setup_app:fee_list')
    else:
        form = FeeForm()
    return render(request, 'setup/fee_form.html', {'form': form, 'title': 'Add Fee'})


@login_required
@admin_or_hq_required
def fee_edit(request, pk):
    fee = get_object_or_404(Fee, pk=pk)
    if request.method == 'POST':
        form = FeeForm(request.POST, instance=fee)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fee updated successfully.')
            return redirect('setup_app:fee_list')
    else:
        form = FeeForm(instance=fee)
    return render(request, 'setup/fee_form.html', {'form': form, 'title': 'Edit Fee'})


@login_required
def panel_list(request):
    panels = Panel.objects.filter(is_active=True)
    return render(request, 'setup/panel_list.html', {'panels': panels})


@login_required
@admin_or_hq_required
def panel_create(request):
    if request.method == 'POST':
        form = PanelForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Panel added successfully.')
            return redirect('setup_app:panel_list')
    else:
        form = PanelForm()
    return render(request, 'setup/panel_form.html', {'form': form, 'title': 'Add Panel'})


@login_required
@admin_or_hq_required
def panel_edit(request, pk):
    panel = get_object_or_404(Panel, pk=pk)
    if request.method == 'POST':
        form = PanelForm(request.POST, instance=panel)
        if form.is_valid():
            form.save()
            messages.success(request, 'Panel updated successfully.')
            return redirect('setup_app:panel_list')
    else:
        form = PanelForm(instance=panel)
    return render(request, 'setup/panel_form.html', {'form': form, 'title': 'Edit Panel'})


@login_required
@admin_required
def audit_log_list(request):
    logs = AuditLog.objects.all()[:100]
    return render(request, 'setup/audit_log_list.html', {'logs': logs})
