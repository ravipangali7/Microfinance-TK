from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from app.models import SupportTicket, SupportTicketReply, SupportTicketStatus
from .helpers import is_admin, is_admin_or_board, get_role_context
from .filter_helpers import (
    get_default_date_range, parse_date_range, format_date_range,
    apply_date_filter, apply_text_search
)


@login_required
def support_ticket_list(request):
    """List all support tickets"""
    # Admin and Board can view all tickets, Members can only view their own
    from app.models import UserStatus
    
    if is_admin_or_board(request.user):
        tickets = SupportTicket.objects.all()
    else:
        tickets = SupportTicket.objects.filter(user=request.user)
    
    # Apply filters
    search = request.GET.get('search', '')
    date_range_str = request.GET.get('date_range', '')
    status = request.GET.get('status', '')
    
    # Apply text search
    if search:
        tickets = apply_text_search(tickets, search, ['subject', 'message', 'user__name', 'user__phone'])
    
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
    tickets = apply_date_filter(tickets, 'created_at', start_date, end_date)
    
    # Apply status filter
    if status:
        tickets = tickets.filter(status=status)
    
    # Order by
    tickets = tickets.order_by('-created_at')
    
    # Calculate stats
    total_tickets = tickets.count()
    pending_tickets = tickets.filter(status=SupportTicketStatus.PENDING).count()
    open_tickets = tickets.filter(status=SupportTicketStatus.OPEN).count()
    resolved_tickets = tickets.filter(status=SupportTicketStatus.RESOLVED).count()
    closed_tickets = tickets.filter(status=SupportTicketStatus.CLOSED).count()
    
    context = {
        'tickets': tickets,
        'stats': {
            'total': total_tickets,
            'pending': pending_tickets,
            'open': open_tickets,
            'resolved': resolved_tickets,
            'closed': closed_tickets,
        },
        'filters': {
            'search': search,
            'date_range': date_range_str,
            'status': status,
        },
        'all_statuses': SupportTicketStatus.choices,
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/support_ticket_list.html', context)


@login_required
def support_ticket_view(request, pk):
    """View support ticket details with replies"""
    ticket = get_object_or_404(SupportTicket, pk=pk)
    
    # Members can only view their own tickets
    from .helpers import is_member
    if is_member(request.user) and ticket.user != request.user:
        messages.error(request, 'Access denied. You can only view your own tickets.')
        return redirect('support_ticket_list')
    
    # Get all replies for this ticket
    replies = SupportTicketReply.objects.filter(ticket=ticket).order_by('created_at')
    
    context = {
        'ticket': ticket,
        'replies': replies,
        'all_statuses': SupportTicketStatus.choices,
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/support_ticket_view.html', context)


@login_required
@require_http_methods(["POST"])
def support_ticket_update_status(request, pk):
    """Update support ticket status (Admin/Board only)"""
    if not is_admin_or_board(request.user):
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)
    
    ticket = get_object_or_404(SupportTicket, pk=pk)
    new_status = request.POST.get('status')
    
    if new_status not in [choice[0] for choice in SupportTicketStatus.choices]:
        return JsonResponse({'success': False, 'error': 'Invalid status.'}, status=400)
    
    ticket.status = new_status
    ticket.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Ticket status updated to {new_status}.'
    })


@login_required
@require_http_methods(["POST"])
def support_ticket_add_reply(request, pk):
    """Add a reply to a support ticket"""
    ticket = get_object_or_404(SupportTicket, pk=pk)
    
    # Members can only reply to their own tickets
    from .helpers import is_member
    if is_member(request.user) and ticket.user != request.user:
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)
    
    message = request.POST.get('message', '').strip()
    image = request.FILES.get('image')
    
    if not message and not image:
        return JsonResponse({'success': False, 'error': 'Message or image is required.'}, status=400)
    
    reply = SupportTicketReply.objects.create(
        ticket=ticket,
        user=request.user,
        message=message,
        image=image if image else None,
    )
    
    # Update ticket status to open if it was pending
    if ticket.status == SupportTicketStatus.PENDING:
        ticket.status = SupportTicketStatus.OPEN
        ticket.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Reply added successfully.',
        'reply_id': reply.id
    })

