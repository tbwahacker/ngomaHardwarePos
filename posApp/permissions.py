from django.http import HttpResponseForbidden
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("You are not allowed to access this page.")
        if not request.user.is_staff:  # or use request.user.is_superuser
            return HttpResponseForbidden("You must be an admin to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def superuser_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("You are not allowed to access this page.")
        if not request.user.is_superuser:  # or use request.user.is_superuser
            return HttpResponseForbidden("You must be a superuser to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view