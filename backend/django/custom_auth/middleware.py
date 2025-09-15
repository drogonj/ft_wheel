from django.shortcuts import redirect
from django.urls import reverse

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
            '/admin',
            '/static/',
            '/favicon.ico',
        ]

        # Check if the user is authenticated and has not given consent
        if request.user.is_authenticated:
            if not request.user.has_consent and request.path not in excluded_routes:
                return redirect(reverse('consent'))
            

        response = self.get_response(request)
        return response