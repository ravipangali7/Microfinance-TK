from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from app.models import FundManagement, WithdrawalStatus, FundManagementType
from app.forms import FundManagementForm, FundManagementCreateForm
from .helpers import is_admin, is_admin_or_board, get_role_context


@login_required
def fund_management_list(request):
    from decimal import Decimal
    from app.models import WithdrawalStatus, FundManagementType
    from .filter_helpers import (
        get_default_date_range, parse_date_range, format_date_range,
        apply_date_filter, apply_amount_range_filter
    )
    
    fund_management = FundManagement.objects.all()
    
    # Apply filters
    status = request.GET.get('status', '')
    fund_type = request.GET.get('type', '')
    from_amount = request.GET.get('from_amount', '')
    to_amount = request.GET.get('to_amount', '')
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
    if status:
        fund_management = fund_management.filter(status=status)
    if fund_type:
        fund_management = fund_management.filter(type=fund_type)
    if from_amount or to_amount:
        fund_management = apply_amount_range_filter(fund_management, 'amount', from_amount, to_amount)
    
    # Apply date filter
    fund_management = apply_date_filter(fund_management, 'date', start_date, end_date)
    
    # Order by
    fund_management = fund_management.order_by('-date', '-created_at')
    
    # Calculate stats from filtered queryset
    total_records = fund_management.count()
    total_amount = sum(fm.amount for fm in fund_management)
    credit_amount = sum(fm.amount for fm in fund_management.filter(type=FundManagementType.CREDIT))
    debit_amount = sum(fm.amount for fm in fund_management.filter(type=FundManagementType.DEBIT))
    pending_count = fund_management.filter(status=WithdrawalStatus.PENDING).count()
    approved_count = fund_management.filter(status=WithdrawalStatus.APPROVED).count()
    rejected_count = fund_management.filter(status=WithdrawalStatus.REJECTED).count()
    credit_count = fund_management.filter(type=FundManagementType.CREDIT).count()
    debit_count = fund_management.filter(type=FundManagementType.DEBIT).count()
    
    context = {
        'fund_management': fund_management,
        'stats': {
            'total': total_records,
            'total_amount': total_amount,
            'credit_amount': credit_amount,
            'debit_amount': debit_amount,
            'pending': pending_count,
            'approved': approved_count,
            'rejected': rejected_count,
            'credit_count': credit_count,
            'debit_count': debit_count,
        },
        'filters': {
            'status': status,
            'type': fund_type,
            'from_amount': from_amount,
            'to_amount': to_amount,
            'date_range': date_range_str,
        },
        'all_statuses': WithdrawalStatus.choices,
        'all_types': FundManagementType.choices,
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/fund_management_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def fund_management_create(request):
    # Only Admin and Board can create fund management records
    if not is_admin_or_board(request.user):
        messages.error(request, 'Access denied. Only Admin and Board members can create fund management records.')
        return redirect('fund_management_list')
    
    if request.method == 'POST':
        form = FundManagementCreateForm(request.POST)
        if form.is_valid():
            obj = form.save()
            return redirect('fund_management_list')
    else:
        form = FundManagementCreateForm()
    
    context = {'form': form}
    context.update(get_role_context(request))
    return render(request, 'core/crud/fund_management_add.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def fund_management_update(request, pk):
    obj = get_object_or_404(FundManagement, pk=pk)
    
    # Only Admin and Board can update fund management records
    if not is_admin_or_board(request.user):
        messages.error(request, 'Access denied. Only Admin and Board members can update fund management records.')
        return redirect('fund_management_list')
    
    # Check if record has been approved/rejected (cannot edit if status is not pending)
    if obj.status != WithdrawalStatus.PENDING:
        messages.error(request, 'This record cannot be edited because it has already been processed.')
        return redirect('fund_management_view', pk=pk)
    
    if request.method == 'POST':
        form = FundManagementForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            return redirect('fund_management_list')
    else:
        form = FundManagementForm(instance=obj)
    
    context = {'form': form, 'obj': obj}
    context.update(get_role_context(request))
    return render(request, 'core/crud/fund_management_edit.html', context)


@login_required
def fund_management_view(request, pk):
    obj = get_object_or_404(FundManagement, pk=pk)
    context = {'obj': obj}
    context.update(get_role_context(request))
    return render(request, 'core/crud/fund_management_view.html', context)


@login_required
@require_http_methods(["POST"])
def fund_management_delete(request, pk):
    # Only Admin can delete fund management records
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied. Only Admin can delete fund management records.'}, status=403)
    
    obj = get_object_or_404(FundManagement, pk=pk)
    obj.delete()
    return JsonResponse({'success': True, 'message': 'Fund Management record deleted successfully'})

