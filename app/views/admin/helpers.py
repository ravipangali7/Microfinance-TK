# Role helper functions
def is_admin(user):
    """Check if user is in Admin group"""
    return user.groups.filter(name='Admin').exists()

def is_board(user):
    """Check if user is in Board group"""
    return user.groups.filter(name='Board').exists()

def is_staff(user):
    """Check if user is in Staff group"""
    return user.groups.filter(name='Staff').exists()

def is_member(user):
    """Check if user is Member (not admin/board/staff)"""
    return not (is_admin(user) or is_board(user) or is_staff(user))

def is_admin_or_board(user):
    """Check if user is in Admin or Board group"""
    return user.groups.filter(name__in=['Admin', 'Board']).exists()

def is_admin_board_or_staff(user):
    """Check if user is in Admin, Board, or Staff group"""
    return user.groups.filter(name__in=['Admin', 'Board', 'Staff']).exists()

def get_role_context(request):
    """Get role context variables for templates"""
    user = request.user
    return {
        'is_admin': is_admin(user),
        'is_board': is_board(user),
        'is_staff': is_staff(user),
        'is_member': is_member(user),
        'is_admin_or_board': is_admin_or_board(user),
        'is_admin_board_or_staff': is_admin_board_or_staff(user),
    }

