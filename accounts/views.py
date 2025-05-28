from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, View
from django.urls import reverse_lazy
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.conf import settings

class SignUpView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('accounts:login')
    template_name = 'registration/signup.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Account created successfully! Please log in.')
        return response

@login_required
def profile(request):
    return render(request, 'registration/profile.html')

class CustomLogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        next_page = request.GET.get('next', settings.LOGOUT_REDIRECT_URL or '/')
        return HttpResponseRedirect(next_page)
