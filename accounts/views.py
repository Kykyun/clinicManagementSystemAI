from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .models import User, AuditLog
from .forms import LoginForm, UserRegistrationForm, UserUpdateForm, StaffForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('management_app:dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            AuditLog.objects.create(
                user=user,
                action='login',
                model_name='User',
                object_id=str(user.id),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect('management_app:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect('management_app:dashboard')
    
    success = False
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            user = User.objects.filter(email=email).first()
            if user:
                AuditLog.objects.create(
                    user=None,
                    action='password_reset_request',
                    model_name='User',
                    object_id=str(user.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    changes=f'Password reset requested for {email}'
                )
            success = True
    
    return render(request, 'accounts/forgot_password.html', {'success': success})


@login_required
def logout_view(request):
    AuditLog.objects.create(
        user=request.user,
        action='logout',
        model_name='User',
        object_id=str(request.user.id),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def staff_list(request):
    if request.user.role not in ['admin', 'hq_staff']:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('management_app:dashboard')
    
    staff = User.objects.all().order_by('role', 'first_name')
    return render(request, 'accounts/staff_list.html', {'staff': staff})


@login_required
def staff_create(request):
    if request.user.role not in ['admin', 'hq_staff']:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('management_app:dashboard')
    
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            else:
                user.set_password('changeme123')
            user.save()
            messages.success(request, f'Staff member {user.get_full_name()} created successfully.')
            return redirect('accounts:staff_list')
    else:
        form = StaffForm()
    return render(request, 'accounts/staff_form.html', {'form': form, 'title': 'Add New Staff'})


@login_required
def staff_edit(request, pk):
    if request.user.role not in ['admin', 'hq_staff']:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('management_app:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()
            messages.success(request, f'Staff member {user.get_full_name()} updated successfully.')
            return redirect('accounts:staff_list')
    else:
        form = StaffForm(instance=user)
    return render(request, 'accounts/staff_form.html', {'form': form, 'title': 'Edit Staff', 'user': user})


@login_required
def staff_delete(request, pk):
    if request.user.role not in ['admin']:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('accounts:staff_list')
    
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user.is_active_staff = False
        user.is_active = False
        user.save()
        messages.success(request, f'Staff member {user.get_full_name()} deactivated.')
        return redirect('accounts:staff_list')
    return render(request, 'accounts/staff_confirm_delete.html', {'user': user})
