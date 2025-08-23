from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin
from .models import AdminActionLog


class AdminAccessMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/admin/'):
            # Add safety check for user attribute
            if not hasattr(request, 'user'):
                return  # Skip processing if user attribute doesn't exist

            # Log admin actions
            if request.method == 'POST' and request.user.is_authenticated:
                action = 'CHANGE' if '_save' in request.POST else 'ADD' if '_addanother' in request.POST else 'DELETE'
                model_name = request.path.split('/')[2].title()
                AdminActionLog.objects.create(
                    user=request.user,
                    action=action,
                    model=model_name,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=str(request.POST)
                )

            # Restrict admin access based on role
            if request.user.is_authenticated and not request.user.is_staff:
                logout(request)
                return redirect(reverse('admin:login') + '?next=' + request.path)

            # IP-based restrictions
            allowed_ips = ['127.0.0.1']  # Add your allowed IPs
            if request.META.get('REMOTE_ADDR') not in allowed_ips:
                logout(request)
                return redirect(reverse('admin:login') + '?error=ip_blocked')


class RoleBasedAccessMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/admin/'):
            # Add safety check for user attribute
            if not hasattr(request, 'user'):
                return  # Skip processing if user attribute doesn't exist

            # Redirect writers to their content list
            if request.user.is_authenticated and request.user.role and request.user.role.name == 'writer':
                if request.path == '/admin/' or request.path == '/admin':
                    return redirect('/admin/cms/content/')