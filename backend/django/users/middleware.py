from django.shortcuts import redirect, render
from django.urls import reverse
from django.http import HttpResponse
from django.template import loader
from administration.models import SiteSettings

class ConsentMiddleware:
    """
    Middleware to handle user acknowledge of TIG, and others bad things.
    Redirects to a consent page if the user has not given consent.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        excluded_routes = [
            reverse('consent'),
            reverse('accept_consent'),
            reverse('login'),
            reverse('logout'),
            reverse('callback'),
            '/static/',
        ]

        # Check if the user is authenticated and has not given consent
        if request.user.is_authenticated:
            if not request.user.has_consent and request.path not in excluded_routes:
                return redirect(reverse('consent'))
            

        response = self.get_response(request)
        return response


class MaintenanceMiddleware:
    """
    Middleware to handle maintenance mode.
    Shows maintenance page to non-admin users when maintenance mode is enabled.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Import here to avoid circular imports
        try:
            settings = SiteSettings.objects.get(pk=1)
            if not settings.maintenance_mode:
                # Maintenance mode is disabled, proceed normally
                response = self.get_response(request)
                return response
        except SiteSettings.DoesNotExist:
            # No settings found, proceed normally
            response = self.get_response(request)
            return response

        # Maintenance mode is enabled
        excluded_routes = [
            '/static/',
            '/logout',
            '/admin/',  # Django admin
        ]
        
        # Allow admin panel access for admins and moderators
        admin_routes = [
            '/adm/',
        ]

        # Check if route should be excluded from maintenance
        for excluded in excluded_routes:
            if request.path.startswith(excluded):
                response = self.get_response(request)
                return response

        # Check if user is admin/moderator accessing admin panel
        for admin_route in admin_routes:
            if request.path.startswith(admin_route):
                if request.user.is_authenticated and (request.user.is_admin() or request.user.is_moderator()):
                    response = self.get_response(request)
                    return response
                # Non-admin trying to access admin during maintenance
                break

        # Allow admins to access the site normally during maintenance
        if request.user.is_authenticated and request.user.is_admin():
            response = self.get_response(request)
            return response

        # Show maintenance page to all other users
        template = loader.get_template('maintenance.html')
        context = {
            'maintenance_message': settings.maintenance_message,
        }
        return HttpResponse(template.render(context, request), status=503)