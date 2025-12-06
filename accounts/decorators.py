from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*allowed_roles):
    """
    Decorator to restrict view access to specific user roles.
    Usage: @role_required('admin', 'finance')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.role not in allowed_roles:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('management_app:dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    """Decorator to restrict view access to admin users only."""
    return role_required('admin')(view_func)


def admin_or_hq_required(view_func):
    """Decorator to restrict view access to admin or HQ staff."""
    return role_required('admin', 'hq_staff')(view_func)


def finance_access_required(view_func):
    """Decorator to restrict view access to finance, admin, or HQ staff."""
    return role_required('admin', 'finance', 'hq_staff')(view_func)


def clinical_staff_required(view_func):
    """Decorator to restrict view access to clinical staff (doctor, nurse, admin)."""
    return role_required('admin', 'doctor', 'nurse')(view_func)


def doctor_required(view_func):
    """Decorator to restrict view access to doctors and admin only."""
    return role_required('admin', 'doctor')(view_func)


def reception_or_higher(view_func):
    """Decorator for reception, nurse, doctor, admin, and HQ staff."""
    return role_required('admin', 'doctor', 'nurse', 'receptionist', 'hq_staff')(view_func)
