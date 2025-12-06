from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from app.models import Penalty, User, PaymentStatus, PenaltyType
from app.forms import PenaltyForm
from .helpers import is_admin_board_or_staff, is_member, get_role_context
from .filter_helpers import (
    get_default_date_range, parse_date_range, format_date_range,
    apply_date_filter, apply_amount_range_filter
)


@login_required
def penalty_list(request):
    user = request.user
    # Members can only see their own penalties
    if is_member(user):
        penalties = Penalty.objects.filter(user=user).select_related('user')
    else:
        penalties = Penalty.objects.all().select_related('user')
    
    # Apply filters
    user_id = request.GET.get('user_id', '')
    penalty_type = request.GET.get('penalty_type', '')
    payment_status = request.GET.get('payment_status', '')
    date_range_str = request.GET.get('date_range', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')
    
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
    
    # Apply filters
    if user_id and not is_member(user):
        penalties = penalties.filter(user_id=user_id)
    if penalty_type:
        penalties = penalties.filter(penalty_type=penalty_type)
    if payment_status:
        penalties = penalties.filter(payment_status=payment_status)
    
    # Apply date filter
    penalties = apply_date_filter(penalties, 'due_date', start_date, end_date)
    
    # Apply amount range filter
    if min_amount or max_amount:
        penalties = apply_amount_range_filter(penalties, 'penalty_amount', min_amount, max_amount)
    
    # Order by
    penalties = penalties.order_by('-due_date', '-created_at')
    
    # Calculate stats from filtered queryset
    total_penalties = penalties.count()
    total_amount = sum(p.penalty_amount for p in penalties)
    pending_penalties = penalties.filter(payment_status=PaymentStatus.PENDING)
    pending_count = pending_penalties.count()
    pending_amount = sum(p.penalty_amount for p in pending_penalties)
    paid_penalties = penalties.filter(payment_status=PaymentStatus.PAID)
    paid_count = paid_penalties.count()
    paid_amount = sum(p.penalty_amount for p in paid_penalties)
    
    context = {
        'penalties': penalties,
        'stats': {
            'total': total_penalties,
            'total_amount': total_amount,
            'pending_count': pending_count,
            'pending_amount': pending_amount,
            'paid_count': paid_count,
            'paid_amount': paid_amount,
        },
        'filters': {
            'user_id': user_id,
            'penalty_type': penalty_type,
            'payment_status': payment_status,
            'date_range': date_range_str,
            'min_amount': min_amount,
            'max_amount': max_amount,
        },
        'all_users': User.objects.all().order_by('name') if not is_member(user) else [],
        'penalty_types': PenaltyType.choices,
        'payment_statuses': PaymentStatus.choices,
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/penalty_list.html', context)


@login_required
def penalty_view(request, pk):
    penalty = get_object_or_404(Penalty, pk=pk)
    
    # Members can only view their own penalties
    if is_member(request.user) and penalty.user != request.user:
        messages.error(request, 'Access denied. You can only view your own penalties.')
        return redirect('penalty_list')
    
    # Get related object info
    related_object = None
    try:
        if penalty.penalty_type == PenaltyType.DEPOSIT:
            from app.models import MonthlyMembershipDeposit
            related_object = MonthlyMembershipDeposit.objects.filter(pk=penalty.related_object_id).first()
        elif penalty.penalty_type == PenaltyType.INTEREST:
            from app.models import LoanInterestPayment
            related_object = LoanInterestPayment.objects.filter(pk=penalty.related_object_id).first()
    except Exception:
        pass
    
    context = {
        'obj': penalty,
        'related_object': related_object,
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/penalty_view.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def penalty_edit(request, pk):
    penalty = get_object_or_404(Penalty, pk=pk)
    
    # Only admin/board/staff can edit penalties
    if not is_admin_board_or_staff(request.user):
        messages.error(request, 'Access denied. Only Admin, Board, and Staff can edit penalties.')
        return redirect('penalty_list')
    
    if request.method == 'POST':
        form = PenaltyForm(request.POST, instance=penalty)
        if form.is_valid():
            obj = form.save()
            messages.success(request, 'Penalty updated successfully.')
            return redirect('penalty_view', pk=obj.pk)
    else:
        form = PenaltyForm(instance=penalty)
    
    context = {'form': form, 'obj': penalty}
    context.update(get_role_context(request))
    return render(request, 'core/crud/penalty_edit.html', context)


@login_required
@require_http_methods(["POST"])
def penalty_mark_paid(request, pk):
    penalty = get_object_or_404(Penalty, pk=pk)
    
    # Only admin/board/staff can mark penalties as paid
    if not is_admin_board_or_staff(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
    
    penalty.payment_status = PaymentStatus.PAID
    if not penalty.paid_date:
        penalty.paid_date = timezone.now().date()
    penalty.save()
    
    return JsonResponse({'success': True, 'message': 'Penalty marked as paid successfully'})


@login_required
@require_http_methods(["POST"])
def penalty_delete(request, pk):
    penalty = get_object_or_404(Penalty, pk=pk)
    
    # Only admin/board/staff can delete penalties
    if not is_admin_board_or_staff(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
    
    penalty.delete()
    return JsonResponse({'success': True, 'message': 'Penalty deleted successfully'})

