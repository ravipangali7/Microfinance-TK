from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from app.models import MonthlyMembershipDeposit, User, MembershipUser, Membership, PaymentStatus
from app.forms import MonthlyMembershipDepositForm
from .helpers import is_admin, is_member, get_role_context
from .filter_helpers import (
    get_default_date_range, parse_date_range, format_date_range,
    apply_date_filter
)


@login_required
def monthly_membership_deposit_list(request):
    user = request.user
    # Members can only see their own deposits
    if is_member(user):
        deposits = MonthlyMembershipDeposit.objects.filter(user=user).select_related('user', 'membership')
    else:
        deposits = MonthlyMembershipDeposit.objects.select_related('user', 'membership')
    
    # Apply filters
    user_id = request.GET.get('user_id', '')
    membership_id = request.GET.get('membership_id', '')
    payment_status = request.GET.get('payment_status', '')
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
    
    # Apply filters
    if user_id and not is_member(user):
        deposits = deposits.filter(user_id=user_id)
    if membership_id:
        deposits = deposits.filter(membership_id=membership_id)
    if payment_status:
        deposits = deposits.filter(payment_status=payment_status)
    
    # Apply date filter
    deposits = apply_date_filter(deposits, 'date', start_date, end_date)
    
    # Order by
    deposits = deposits.order_by('-date', '-created_at')
    
    # Calculate stats from filtered queryset
    total_deposits = deposits.count()
    total_amount = sum(d.amount for d in deposits)
    paid_deposits = deposits.filter(payment_status=PaymentStatus.PAID)
    paid_count = paid_deposits.count()
    paid_amount = sum(d.amount for d in paid_deposits)
    pending_deposits = deposits.filter(payment_status=PaymentStatus.PENDING)
    pending_count = pending_deposits.count()
    pending_amount = sum(d.amount for d in pending_deposits)
    
    context = {
        'deposits': deposits,
        'stats': {
            'total': total_deposits,
            'total_amount': total_amount,
            'paid_count': paid_count,
            'paid_amount': paid_amount,
            'pending_count': pending_count,
            'pending_amount': pending_amount,
        },
        'filters': {
            'user_id': user_id,
            'membership_id': membership_id,
            'payment_status': payment_status,
            'date_range': date_range_str,
        },
        'all_users': User.objects.all().order_by('name') if not is_member(user) else [],
        'all_memberships': Membership.objects.all().order_by('name'),
        'payment_statuses': PaymentStatus.choices,
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/monthly_membership_deposit_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def monthly_membership_deposit_create(request):
    # Members cannot create deposits
    if is_member(request.user):
        messages.error(request, 'Access denied. Members cannot create deposits.')
        return redirect('monthly_membership_deposit_list')
    
    if request.method == 'POST':
        form = MonthlyMembershipDepositForm(request.POST)
        if form.is_valid():
            obj = form.save()
            return redirect('monthly_membership_deposit_list')
    else:
        form = MonthlyMembershipDepositForm()
    
    context = {'form': form}
    context.update(get_role_context(request))
    return render(request, 'core/crud/monthly_membership_deposit_add.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def monthly_membership_deposit_update(request, pk):
    obj = get_object_or_404(MonthlyMembershipDeposit, pk=pk)
    
    # Members cannot edit deposits
    if is_member(request.user):
        if obj.user != request.user:
            messages.error(request, 'Access denied. You can only edit your own deposits.')
            return redirect('monthly_membership_deposit_list')
        messages.error(request, 'Access denied. Members cannot edit deposits.')
        return redirect('monthly_membership_deposit_list')
    
    if request.method == 'POST':
        form = MonthlyMembershipDepositForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            return redirect('monthly_membership_deposit_list')
    else:
        form = MonthlyMembershipDepositForm(instance=obj)
    
    context = {'form': form, 'obj': obj}
    context.update(get_role_context(request))
    return render(request, 'core/crud/monthly_membership_deposit_edit.html', context)


@login_required
def monthly_membership_deposit_view(request, pk):
    obj = get_object_or_404(MonthlyMembershipDeposit, pk=pk)
    
    # Members can only view their own deposits
    if is_member(request.user) and obj.user != request.user:
        messages.error(request, 'Access denied. You can only view your own deposits.')
        return redirect('monthly_membership_deposit_list')
    
    context = {'obj': obj}
    context.update(get_role_context(request))
    return render(request, 'core/crud/monthly_membership_deposit_view.html', context)


@login_required
@require_http_methods(["POST"])
def monthly_membership_deposit_delete(request, pk):
    obj = get_object_or_404(MonthlyMembershipDeposit, pk=pk)
    
    # Members cannot delete deposits
    if is_member(request.user):
        if obj.user != request.user:
            return JsonResponse({'success': False, 'message': 'Access denied. You can only delete your own deposits.'}, status=403)
        return JsonResponse({'success': False, 'message': 'Access denied. Members cannot delete deposits.'}, status=403)
    
    obj.delete()
    return JsonResponse({'success': True, 'message': 'Monthly Membership Deposit deleted successfully'})


@login_required
def get_user_memberships(request, user_id):
    """API endpoint to get user's memberships with amounts"""
    user = get_object_or_404(User, pk=user_id)
    
    # Get user's memberships
    membership_users = MembershipUser.objects.filter(user=user).select_related('membership').order_by('-created_at')
    
    memberships = []
    for mu in membership_users:
        memberships.append({
            'id': mu.membership.id,
            'name': mu.membership.name,
            'amount': str(mu.membership.amount)
        })
    
    return JsonResponse({
        'success': True,
        'memberships': memberships,
        'count': len(memberships)
    })

