from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from app.models import OrganizationalWithdrawal, WithdrawalStatus
from app.forms import OrganizationalWithdrawalForm, OrganizationalWithdrawalCreateForm
from .helpers import is_admin, is_admin_or_board, get_role_context


@login_required
def organizational_withdrawal_list(request):
    withdrawals = OrganizationalWithdrawal.objects.all().order_by('-date', '-created_at')
    context = {
        'withdrawals': withdrawals,
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/organizational_withdrawal_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def organizational_withdrawal_create(request):
    # Only Admin and Board can create withdrawals
    if not is_admin_or_board(request.user):
        messages.error(request, 'Access denied. Only Admin and Board members can create organizational withdrawals.')
        return redirect('organizational_withdrawal_list')
    
    if request.method == 'POST':
        form = OrganizationalWithdrawalCreateForm(request.POST)
        if form.is_valid():
            obj = form.save()
            return redirect('organizational_withdrawal_list')
    else:
        form = OrganizationalWithdrawalCreateForm()
    
    context = {'form': form}
    context.update(get_role_context(request))
    return render(request, 'core/crud/organizational_withdrawal_add.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def organizational_withdrawal_update(request, pk):
    obj = get_object_or_404(OrganizationalWithdrawal, pk=pk)
    
    # Only Admin and Board can update withdrawals
    if not is_admin_or_board(request.user):
        messages.error(request, 'Access denied. Only Admin and Board members can update organizational withdrawals.')
        return redirect('organizational_withdrawal_list')
    
    # Check if withdrawal has been approved/rejected (cannot edit if status is not pending)
    if obj.status != WithdrawalStatus.PENDING:
        messages.error(request, 'This withdrawal cannot be edited because it has already been processed.')
        return redirect('organizational_withdrawal_view', pk=pk)
    
    if request.method == 'POST':
        form = OrganizationalWithdrawalForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            return redirect('organizational_withdrawal_list')
    else:
        form = OrganizationalWithdrawalForm(instance=obj)
    
    context = {'form': form, 'obj': obj}
    context.update(get_role_context(request))
    return render(request, 'core/crud/organizational_withdrawal_edit.html', context)


@login_required
def organizational_withdrawal_view(request, pk):
    obj = get_object_or_404(OrganizationalWithdrawal, pk=pk)
    context = {'obj': obj}
    context.update(get_role_context(request))
    return render(request, 'core/crud/organizational_withdrawal_view.html', context)


@login_required
@require_http_methods(["POST"])
def organizational_withdrawal_delete(request, pk):
    # Only Admin can delete withdrawals
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied. Only Admin can delete organizational withdrawals.'}, status=403)
    
    obj = get_object_or_404(OrganizationalWithdrawal, pk=pk)
    obj.delete()
    return JsonResponse({'success': True, 'message': 'Organizational Withdrawal deleted successfully'})

