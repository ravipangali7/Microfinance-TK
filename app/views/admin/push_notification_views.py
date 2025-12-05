from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from app.models import PushNotification
from app.forms import PushNotificationForm
from app.services.push_notification_service import send_push_notification
from .helpers import is_admin, is_member, get_role_context
import logging

logger = logging.getLogger(__name__)


@login_required
def push_notification_list(request):
    """List all push notifications"""
    from .filter_helpers import (
        get_default_date_range, parse_date_range, format_date_range,
        apply_date_filter
    )
    
    # Only admin can view push notifications
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can view push notifications.')
        return redirect('dashboard')
    
    notifications = PushNotification.objects.all()
    
    # Apply filters
    date_range_str = request.GET.get('date_range', '')
    
    # Parse date range
    start_date, end_date = None, None
    if date_range_str:
        date_range = parse_date_range(date_range_str)
        if date_range:
            start_date, end_date = date_range
    else:
        # Default to last 1 month
        start_date, end_date = get_default_date_range()
        date_range_str = format_date_range(start_date, end_date)
    
    # Apply date filter
    notifications = apply_date_filter(notifications, 'created_at', start_date, end_date)
    
    # Order by
    notifications = notifications.order_by('-created_at')
    
    # Calculate stats
    total_notifications = notifications.count()
    
    context = {
        'notifications': notifications,
        'stats': {
            'total': total_notifications,
        },
        'filters': {
            'date_range': date_range_str,
        },
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/push_notification_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def push_notification_create(request):
    """Create a new push notification"""
    # Only admin can create push notifications
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can create push notifications.')
        return redirect('push_notification_list')
    
    if request.method == 'POST':
        form = PushNotificationForm(request.POST, request.FILES)
        if form.is_valid():
            notification = form.save()
            messages.success(request, 'Push notification created successfully.')
            return redirect('push_notification_list')
    else:
        form = PushNotificationForm()
    
    context = {'form': form}
    context.update(get_role_context(request))
    return render(request, 'core/crud/push_notification_add.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def push_notification_update(request, pk):
    """Update a push notification"""
    # Only admin can update push notifications
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can update push notifications.')
        return redirect('push_notification_list')
    
    notification = get_object_or_404(PushNotification, pk=pk)
    
    if request.method == 'POST':
        form = PushNotificationForm(request.POST, request.FILES, instance=notification)
        if form.is_valid():
            notification = form.save()
            messages.success(request, 'Push notification updated successfully.')
            return redirect('push_notification_view', pk=pk)
    else:
        form = PushNotificationForm(instance=notification)
    
    context = {'form': form, 'notification': notification}
    context.update(get_role_context(request))
    return render(request, 'core/crud/push_notification_edit.html', context)


@login_required
def push_notification_view(request, pk):
    """View push notification details"""
    # Only admin can view push notifications
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can view push notifications.')
        return redirect('push_notification_list')
    
    notification = get_object_or_404(PushNotification, pk=pk)
    
    context = {
        'notification': notification,
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/push_notification_view.html', context)


@login_required
@require_http_methods(["POST"])
def push_notification_delete(request, pk):
    """Delete a push notification"""
    # Only admin can delete push notifications
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can delete push notifications.')
        return redirect('push_notification_list')
    
    notification = get_object_or_404(PushNotification, pk=pk)
    
    notification.delete()
    messages.success(request, 'Push notification deleted successfully.')
    return redirect('push_notification_list')


@login_required
@require_http_methods(["POST"])
def send_push_notification_view(request, pk):
    """Send a push notification to all users (can be sent multiple times)"""
    # Only admin can send push notifications
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Access denied. Only Admin can send push notifications.'}, status=403)
    
    notification = get_object_or_404(PushNotification, pk=pk)
    
    try:
        # Send notification using the service (allows unlimited sends)
        stats = send_push_notification(notification, request.user)
        
        return JsonResponse({
            'success': True,
            'message': f'Notification sent successfully to {stats["successful"]} users.',
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error sending push notification: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Failed to send notification: {str(e)}'
        }, status=500)

