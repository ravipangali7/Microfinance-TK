from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from app.models import MySetting
from app.forms import MySettingForm
from .helpers import is_admin, get_role_context


@login_required
def mysetting_view(request):
    # Only Admin can view settings
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can view settings.')
        return redirect('dashboard')
    
    settings = MySetting.get_settings()
    context = {'obj': settings}
    context.update(get_role_context(request))
    return render(request, 'core/crud/mysetting_view.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def mysetting_update(request):
    # Only Admin can update settings
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can update settings.')
        return redirect('dashboard')
    
    settings = MySetting.get_settings()
    
    if request.method == 'POST':
        form = MySettingForm(request.POST, request.FILES, instance=settings)
        if form.is_valid():
            obj = form.save()
            messages.success(request, 'Settings updated successfully.')
            return redirect('mysetting_view')
    else:
        form = MySettingForm(instance=settings)
    
    context = {'form': form, 'obj': settings}
    context.update(get_role_context(request))
    return render(request, 'core/crud/mysetting_edit.html', context)

