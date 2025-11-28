from rest_framework import authentication
from rest_framework import exceptions
from app.models import User


class PhoneAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication class that authenticates users based on phone number
    sent in the X-User-Phone header.
    """
    
    def authenticate(self, request):
        phone = request.META.get('HTTP_X_USER_PHONE')
        
        if not phone:
            # No phone provided - return None to allow other auth methods
            return None
        
        try:
            user = User.objects.get(phone=phone, is_active=True)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid phone number or user not found.')
        except User.MultipleObjectsReturned:
            # This shouldn't happen if phone is unique, but handle it
            user = User.objects.filter(phone=phone, is_active=True).first()
            if not user:
                raise exceptions.AuthenticationFailed('Invalid phone number or user not found.')
        
        return (user, None)  # Return (user, token) tuple - token is None for phone auth

