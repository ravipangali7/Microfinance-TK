from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from app.models import Loan, LoanStatus, FundManagement, WithdrawalStatus
from .helpers import is_admin_or_board, get_role_context


@login_required
def board_approval_view(request):
    """Board approval page - accessible by Admin and Board group members"""
    # Check if user is in Admin or Board group
    if not is_admin_or_board(request.user):
        messages.error(request, 'Access denied. Only Admin and Board members can access this page.')
        return redirect('dashboard')
    
    # Get pending loans
    pending_loans = Loan.objects.filter(status=LoanStatus.PENDING).select_related('user').order_by('-applied_date', '-created_at')
    
    # Get pending fund management records
    pending_fund_management = FundManagement.objects.filter(status=WithdrawalStatus.PENDING).order_by('-date', '-created_at')
    
    context = {
        'pending_loans': pending_loans,
        'pending_fund_management': pending_fund_management,
    }
    context.update(get_role_context(request))
    return render(request, 'core/board_approval.html', context)


@login_required
@require_http_methods(["POST"])
def approve_loan(request, pk):
    """Approve a loan - Admin and Board members"""
    if not is_admin_or_board(request.user):
        messages.error(request, 'Access denied. Only Admin and Board members can approve loans.')
        return redirect('board_approval')
    
    loan = get_object_or_404(Loan, pk=pk, status=LoanStatus.PENDING)
    loan.status = LoanStatus.APPROVED
    loan.action_by = request.user
    loan.approved_date = timezone.now().date()
    loan.save()
    
    messages.success(request, f'Loan #{loan.id} has been approved successfully.')
    return redirect('board_approval')


@login_required
@require_http_methods(["POST"])
def reject_loan(request, pk):
    """Reject a loan - Admin and Board members"""
    if not is_admin_or_board(request.user):
        messages.error(request, 'Access denied. Only Admin and Board members can reject loans.')
        return redirect('board_approval')
    
    loan = get_object_or_404(Loan, pk=pk, status=LoanStatus.PENDING)
    loan.status = LoanStatus.REJECTED
    loan.action_by = request.user
    loan.save()
    
    messages.success(request, f'Loan #{loan.id} has been rejected.')
    return redirect('board_approval')


@login_required
@require_http_methods(["POST"])
def update_loan_status(request, pk):
    """Update loan status - Admin and Board members only"""
    if not is_admin_or_board(request.user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Access denied. Only Admin and Board members can update loan status.'}, status=403)
        messages.error(request, 'Access denied. Only Admin and Board members can update loan status.')
        return redirect('dashboard')
    
    loan = get_object_or_404(Loan, pk=pk)
    new_status = request.POST.get('status')
    
    if not new_status or new_status not in [choice[0] for choice in LoanStatus.choices]:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid status provided.'}, status=400)
        messages.error(request, 'Invalid status provided.')
        return redirect('dashboard')
    
    old_status = loan.status
    loan.status = new_status
    loan.action_by = request.user
    
    # Set dates based on status
    if new_status == LoanStatus.APPROVED and old_status != LoanStatus.APPROVED:
        loan.approved_date = timezone.now().date()
    elif new_status == LoanStatus.ACTIVE and old_status != LoanStatus.ACTIVE:
        loan.disbursed_date = timezone.now().date()
    elif new_status == LoanStatus.COMPLETED and old_status != LoanStatus.COMPLETED:
        loan.completed_date = timezone.now().date()
    
    loan.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': f'Loan #{loan.id} status updated to {loan.get_status_display()} successfully.'})
    
    messages.success(request, f'Loan #{loan.id} status updated to {loan.get_status_display()} successfully.')
    return redirect('dashboard')


@login_required
@require_http_methods(["POST"])
def approve_fund_management(request, pk):
    """Approve a fund management record - Admin and Board members"""
    if not is_admin_or_board(request.user):
        messages.error(request, 'Access denied. Only Admin and Board members can approve fund management records.')
        return redirect('board_approval')
    
    from app.models import FundManagement, WithdrawalStatus
    record = get_object_or_404(FundManagement, pk=pk, status=WithdrawalStatus.PENDING)
    record.status = WithdrawalStatus.APPROVED
    record.save()
    
    messages.success(request, f'Fund Management #{record.id} has been approved successfully.')
    return redirect('board_approval')


@login_required
@require_http_methods(["POST"])
def reject_fund_management(request, pk):
    """Reject a fund management record - Admin and Board members"""
    if not is_admin_or_board(request.user):
        messages.error(request, 'Access denied. Only Admin and Board members can reject fund management records.')
        return redirect('board_approval')
    
    from app.models import FundManagement, WithdrawalStatus
    record = get_object_or_404(FundManagement, pk=pk, status=WithdrawalStatus.PENDING)
    record.status = WithdrawalStatus.REJECTED
    record.save()
    
    messages.success(request, f'Fund Management #{record.id} has been rejected.')
    return redirect('board_approval')


@login_required
@require_http_methods(["POST"])
def update_fund_management_status(request, pk):
    """Update fund management status - Admin and Board members only"""
    if not is_admin_or_board(request.user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Access denied. Only Admin and Board members can update fund management status.'}, status=403)
        messages.error(request, 'Access denied. Only Admin and Board members can update fund management status.')
        return redirect('dashboard')
    
    from app.models import FundManagement, WithdrawalStatus
    record = get_object_or_404(FundManagement, pk=pk)
    new_status = request.POST.get('status')
    
    if not new_status or new_status not in [choice[0] for choice in WithdrawalStatus.choices]:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid status provided.'}, status=400)
        messages.error(request, 'Invalid status provided.')
        return redirect('dashboard')
    
    old_status = record.status
    record.status = new_status
    record.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': f'Fund Management #{record.id} status updated to {record.get_status_display()} successfully.'})
    
    messages.success(request, f'Fund Management #{record.id} status updated to {record.get_status_display()} successfully.')
    return redirect('dashboard')

