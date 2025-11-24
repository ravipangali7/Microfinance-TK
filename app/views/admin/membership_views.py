from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from app.models import Membership, MembershipUser, User
from app.forms import MembershipForm
from .helpers import is_admin, get_role_context


@login_required
def membership_list(request):
    memberships = Membership.objects.all().order_by('name')
    context = {'memberships': memberships}
    context.update(get_role_context(request))
    return render(request, 'core/crud/membership_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def membership_create(request):
    # Only Admin can create memberships
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can create memberships.')
        return redirect('membership_list')
    
    if request.method == 'POST':
        form = MembershipForm(request.POST)
        if form.is_valid():
            obj = form.save()
            return redirect('membership_list')
    else:
        form = MembershipForm()
    context = {'form': form}
    context.update(get_role_context(request))
    return render(request, 'core/crud/membership_add.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def membership_update(request, pk):
    # Only Admin can update memberships
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Only Admin can update memberships.')
        return redirect('membership_list')
    
    obj = get_object_or_404(Membership, pk=pk)
    if request.method == 'POST':
        form = MembershipForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            return redirect('membership_list')
    else:
        form = MembershipForm(instance=obj)
    context = {'form': form, 'obj': obj}
    context.update(get_role_context(request))
    return render(request, 'core/crud/membership_edit.html', context)


@login_required
def membership_view(request, pk):
    obj = get_object_or_404(Membership, pk=pk)
    
    # Get users currently assigned to this membership
    assigned_users = MembershipUser.objects.filter(membership=obj).select_related('user').order_by('-created_at')
    assigned_user_ids = [mu.user.id for mu in assigned_users]
    
    # Get available users (not assigned to this membership)
    available_users = User.objects.exclude(id__in=assigned_user_ids).order_by('name')
    
    context = {
        'obj': obj,
        'assigned_users': assigned_users,
        'available_users': available_users,
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/membership_view.html', context)


@login_required
@require_http_methods(["POST"])
def membership_delete(request, pk):
    # Only Admin can delete memberships
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied. Only Admin can delete memberships.'}, status=403)
    
    obj = get_object_or_404(Membership, pk=pk)
    obj.delete()
    return JsonResponse({'success': True, 'message': 'Membership deleted successfully'})


@login_required
@require_http_methods(["POST"])
def assign_user_to_membership(request, membership_id, user_id):
    """Assign a user to a membership"""
    # Only Admin can assign users
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied. Only Admin can assign users.'}, status=403)
    
    membership = get_object_or_404(Membership, pk=membership_id)
    user = get_object_or_404(User, pk=user_id)
    
    # Check if assignment already exists
    if MembershipUser.objects.filter(user=user, membership=membership).exists():
        return JsonResponse({'success': False, 'message': 'User is already assigned to this membership.'}, status=400)
    
    # Create assignment
    MembershipUser.objects.create(user=user, membership=membership)
    
    return JsonResponse({
        'success': True,
        'message': f'Successfully assigned {user.name} to {membership.name}.'
    })


@login_required
@require_http_methods(["POST"])
def remove_user_from_membership(request, membership_id, user_id):
    """Remove a user from a membership"""
    # Only Admin can remove users
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied. Only Admin can remove users.'}, status=403)
    
    membership = get_object_or_404(Membership, pk=membership_id)
    user = get_object_or_404(User, pk=user_id)
    
    # Find and delete assignment
    membership_user = MembershipUser.objects.filter(user=user, membership=membership).first()
    if not membership_user:
        return JsonResponse({'success': False, 'message': 'User assignment not found.'}, status=404)
    
    membership_user.delete()
    
    return JsonResponse({
        'success': True,
        'message': f'Successfully removed {user.name} from {membership.name}.'
    })

