from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from app.models import Popup
from app.forms import PopupForm
from .helpers import is_admin, get_role_context
from .filter_helpers import (
    parse_date_range, format_date_range,
    apply_text_search
)


@login_required
def popup_list(request):
    """List all popups"""
    # Only admin can view popups
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can view popups.')
        return redirect('dashboard')
    
    # Get all popups for stats calculation (unfiltered)
    all_popups = Popup.objects.all()
    
    # Calculate stats from ALL popups (not filtered)
    total_popups = all_popups.count()
    active_popups = all_popups.filter(is_active=True).count()
    inactive_popups = all_popups.filter(is_active=False).count()
    
    # Start with all popups for filtering
    popups = Popup.objects.all()
    
    # Apply filters
    search = request.GET.get('search', '').strip()
    date_range_str = request.GET.get('date_range', '').strip()
    is_active = request.GET.get('is_active', '').strip()
    
    # Apply text search
    if search:
        popups = apply_text_search(popups, search, ['title', 'description'])
    
    # Parse date range - only apply if explicitly set by user (not empty/whitespace)
    start_date, end_date = None, None
    if date_range_str:
        date_range = parse_date_range(date_range_str)
        if date_range:
            start_date, end_date = date_range
            # Apply date filter using __date lookup (handles timezone automatically)
            if start_date:
                popups = popups.filter(created_at__date__gte=start_date)
            if end_date:
                popups = popups.filter(created_at__date__lte=end_date)
    
    # Apply is_active filter
    if is_active == 'true':
        popups = popups.filter(is_active=True)
    elif is_active == 'false':
        popups = popups.filter(is_active=False)
    
    # Order by
    popups = popups.order_by('-created_at')
    
    context = {
        'popups': popups,
        'stats': {
            'total': total_popups,
            'active': active_popups,
            'inactive': inactive_popups,
        },
        'filters': {
            'search': search,
            'date_range': date_range_str or '',  # Ensure empty string if None
            'is_active': is_active,
        },
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/popup_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def popup_create(request):
    """Create a new popup"""
    # Only admin can create popups
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can create popups.')
        return redirect('popup_list')
    
    if request.method == 'POST':
        form = PopupForm(request.POST, request.FILES)
        if form.is_valid():
            popup = form.save()
            messages.success(request, 'Popup created successfully.')
            # Redirect without filters so the new popup is visible
            return redirect('popup_list')
    else:
        form = PopupForm()
    
    context = {'form': form}
    context.update(get_role_context(request))
    return render(request, 'core/crud/popup_add.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def popup_update(request, pk):
    """Update a popup"""
    # Only admin can update popups
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can update popups.')
        return redirect('popup_list')
    
    popup = get_object_or_404(Popup, pk=pk)
    
    if request.method == 'POST':
        form = PopupForm(request.POST, request.FILES, instance=popup)
        if form.is_valid():
            popup = form.save()
            messages.success(request, 'Popup updated successfully.')
            return redirect('popup_view', pk=pk)
    else:
        form = PopupForm(instance=popup)
    
    context = {'form': form, 'popup': popup}
    context.update(get_role_context(request))
    return render(request, 'core/crud/popup_edit.html', context)


@login_required
def popup_view(request, pk):
    """View popup details"""
    # Only admin can view popups
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can view popups.')
        return redirect('popup_list')
    
    popup = get_object_or_404(Popup, pk=pk)
    
    context = {
        'popup': popup,
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/popup_view.html', context)


@login_required
@require_http_methods(["POST"])
def popup_delete(request, pk):
    """Delete a popup"""
    # Only admin can delete popups
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can delete popups.')
        return redirect('popup_list')
    
    popup = get_object_or_404(Popup, pk=pk)
    
    popup.delete()
    messages.success(request, 'Popup deleted successfully.')
    return redirect('popup_list')

