from django.shortcuts import redirect
from django.urls import reverse

class AlreadyLoggedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.path in [reverse('login'), reverse('signup')]:
            return redirect('home')  # Replace 'home' with the desired URL
        return self.get_response(request)