from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from app.models import User, UserStatus


def login_view(request):
    """Login view with detailed error messages"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        
        if not phone or not password:
            messages.error(request, 'Please provide both phone number and password.')
        else:
            # Check if user exists
            try:
                user = User.objects.get(phone=phone)
                
                # Check if user is active
                if not user.is_active:
                    messages.error(request, 'Your account is inactive. Please contact administrator.')
                # Check if user status is freeze
                elif user.status == UserStatus.FREEZE:
                    messages.warning(request, 'Your account is frozen. Please contact administrator.')
                # Check if user status is inactive
                elif user.status == UserStatus.INACTIVE:
                    messages.warning(request, 'Your account is inactive. Please contact administrator.')
                # Try to authenticate
                else:
                    user = authenticate(request, username=phone, password=password)
                    if user is not None:
                        login(request, user)
                        messages.success(request, f'Welcome back, {user.name}!')
                        next_url = request.GET.get('next', '/')
                        return redirect(next_url)
                    else:
                        messages.error(request, 'Invalid password. Please check your password and try again.')
                        
            except User.DoesNotExist:
                messages.error(request, 'Phone number not found. Please check your phone number and try again.')
            except Exception as e:
                messages.error(request, 'An error occurred during login. Please try again.')
    
    return render(request, 'core/auth/login.html')


def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

