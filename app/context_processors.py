def role_context(request):
    """Context processor to add role information to all templates"""
    if not request.user.is_authenticated:
        return {
            'is_admin': False,
            'is_board': False,
            'is_staff': False,
            'is_member': False,
            'is_admin_or_board': False,
            'is_admin_board_or_staff': False,
        }
    
    from .views.admin.helpers import (
        is_admin, is_board, is_staff, is_member,
        is_admin_or_board, is_admin_board_or_staff
    )
    
    return {
        'is_admin': is_admin(request.user),
        'is_board': is_board(request.user),
        'is_staff': is_staff(request.user),
        'is_member': is_member(request.user),
        'is_admin_or_board': is_admin_or_board(request.user),
        'is_admin_board_or_staff': is_admin_board_or_staff(request.user),
    }

