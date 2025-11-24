from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from app.models import User, Membership, MembershipUser
from app.forms import UserForm
from .helpers import is_admin, is_admin_or_board, is_member, get_role_context


@login_required
def user_list(request):
    # Only Admin and Board can view users list
    if not is_admin_or_board(request.user):
        messages.error(request, 'Access denied. Only Admin and Board members can view users.')
        return redirect('dashboard')
    
    users = User.objects.all().order_by('-created_at')
    context = {'users': users}
    context.update(get_role_context(request))
    return render(request, 'core/crud/user_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def user_create(request):
    # Only Admin can create users
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can create users.')
        return redirect('user_list')
    
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('user_list')
    else:
        form = UserForm()
    context = {'form': form}
    context.update(get_role_context(request))
    return render(request, 'core/crud/user_add.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def user_update(request, pk):
    # Only Admin can update users
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can update users.')
        return redirect('user_list')
    
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            return redirect('user_list')
    else:
        form = UserForm(instance=user)
    context = {'form': form, 'user': user}
    context.update(get_role_context(request))
    return render(request, 'core/crud/user_edit.html', context)


@login_required
@require_http_methods(["POST"])
def user_delete(request, pk):
    # Only Admin can delete users
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied. Only Admin can delete users.'}, status=403)
    
    user = get_object_or_404(User, pk=pk)
    user.delete()
    return JsonResponse({'success': True, 'message': 'User deleted successfully'})


@login_required
def user_view(request, pk):
    # Admin and Board can view any user, Members can only view themselves
    user = get_object_or_404(User, pk=pk)
    
    if is_member(request.user) and request.user.id != user.id:
        messages.error(request, 'Access denied. You can only view your own profile.')
        return redirect('dashboard')
    
    if not is_admin_or_board(request.user) and request.user.id != user.id:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    # Get user's current memberships
    user_memberships = MembershipUser.objects.filter(user=user).select_related('membership').order_by('-created_at')
    user_membership_ids = [mu.membership.id for mu in user_memberships]
    
    # Get available memberships (not assigned to this user)
    available_memberships = Membership.objects.exclude(id__in=user_membership_ids).order_by('name')
    
    context = {
        'user': user,
        'user_memberships': user_memberships,
        'available_memberships': available_memberships,
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/user_view.html', context)


@login_required
@require_http_methods(["POST"])
def assign_membership_to_user(request, user_id, membership_id):
    """Assign a membership to a user"""
    # Only Admin can assign memberships
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied. Only Admin can assign memberships.'}, status=403)
    
    user = get_object_or_404(User, pk=user_id)
    membership = get_object_or_404(Membership, pk=membership_id)
    
    # Check if assignment already exists
    if MembershipUser.objects.filter(user=user, membership=membership).exists():
        return JsonResponse({'success': False, 'message': 'User is already assigned to this membership.'}, status=400)
    
    # Create assignment
    MembershipUser.objects.create(user=user, membership=membership)
    
    return JsonResponse({
        'success': True,
        'message': f'Successfully assigned {membership.name} to {user.name}.'
    })


@login_required
@require_http_methods(["POST"])
def remove_membership_from_user(request, user_id, membership_id):
    """Remove a membership from a user"""
    # Only Admin can remove memberships
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied. Only Admin can remove memberships.'}, status=403)
    
    user = get_object_or_404(User, pk=user_id)
    membership = get_object_or_404(Membership, pk=membership_id)
    
    # Find and delete assignment
    membership_user = MembershipUser.objects.filter(user=user, membership=membership).first()
    if not membership_user:
        return JsonResponse({'success': False, 'message': 'Membership assignment not found.'}, status=404)
    
    membership_user.delete()
    
    return JsonResponse({
        'success': True,
        'message': f'Successfully removed {membership.name} from {user.name}.'
    })

