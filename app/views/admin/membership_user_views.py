from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from app.models import MembershipUser
from app.forms import MembershipUserForm
from .helpers import is_admin, get_role_context


@login_required
def membership_user_list(request):
    membership_users = MembershipUser.objects.all().select_related('user', 'membership').order_by('-created_at')
    context = {'membership_users': membership_users}
    context.update(get_role_context(request))
    return render(request, 'core/crud/membership_user_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def membership_user_create(request):
    # Only Admin can create membership users
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can create membership users.')
        return redirect('membership_user_list')
    
    if request.method == 'POST':
        form = MembershipUserForm(request.POST)
        if form.is_valid():
            obj = form.save()
            return redirect('membership_user_list')
    else:
        form = MembershipUserForm()
    context = {'form': form}
    context.update(get_role_context(request))
    return render(request, 'core/crud/membership_user_add.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def membership_user_update(request, pk):
    # Only Admin can update membership users
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can update membership users.')
        return redirect('membership_user_list')
    
    obj = get_object_or_404(MembershipUser, pk=pk)
    if request.method == 'POST':
        form = MembershipUserForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            return redirect('membership_user_list')
    else:
        form = MembershipUserForm(instance=obj)
    context = {'form': form, 'obj': obj}
    context.update(get_role_context(request))
    return render(request, 'core/crud/membership_user_edit.html', context)


@login_required
def membership_user_view(request, pk):
    obj = get_object_or_404(MembershipUser, pk=pk)
    context = {'obj': obj}
    context.update(get_role_context(request))
    return render(request, 'core/crud/membership_user_view.html', context)


@login_required
@require_http_methods(["POST"])
def membership_user_delete(request, pk):
    # Only Admin can delete membership users
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied. Only Admin can delete membership users.'}, status=403)
    
    obj = get_object_or_404(MembershipUser, pk=pk)
    obj.delete()
    return JsonResponse({'success': True, 'message': 'Membership User deleted successfully'})

