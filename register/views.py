from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .forms import LoginForm, RegisterForm


@csrf_protect
@transaction.atomic
def register_user(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
            except ValueError as exc:
                form.add_error(None, str(exc))
            else:
                login(request, user)
                messages.success(request, 'Welcome! Your account has been created.')
                return redirect('dashboard')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = RegisterForm()
    return render(request, 'register/register.html', {'form': form})


@csrf_protect
def login_user(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}.')
                return redirect('dashboard')
            messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'register/login.html', {'form': form})


@login_required
@require_POST
@csrf_protect
def logout_user(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')
