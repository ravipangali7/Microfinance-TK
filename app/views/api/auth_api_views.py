from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from app.models import User, UserStatus
from app.serializers import LoginSerializer, UserSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    """API endpoint for user login with phone-based authentication"""
    serializer = LoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Check user status
        if user.status == UserStatus.FREEZE:
            return Response(
                {'error': 'Your account is frozen. Please contact administrator.'},
                status=status.HTTP_403_FORBIDDEN
            )
        if user.status == UserStatus.INACTIVE:
            return Response(
                {'error': 'Your account is inactive. Please contact administrator.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Serialize user data (includes groups/roles)
        user_serializer = UserSerializer(user)
        
        # Return user data with roles - no token needed
        return Response({
            'success': True,
            'user': user_serializer.data,
            'user_roles': [group.name for group in user.groups.all()],
            'user_phone': user.phone
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_api(request):
    """API endpoint for user logout"""
    # No token to delete with phone-based auth
    # Just return success message
    return Response(
        {
            'success': True,
            'message': 'Successfully logged out.',
            'user_roles': [group.name for group in request.user.groups.all()],
            'user_phone': request.user.phone
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_api(request):
    """API endpoint to get current authenticated user"""
    serializer = UserSerializer(request.user)
    return Response({
        **serializer.data,
        'user_roles': [group.name for group in request.user.groups.all()],
        'user_phone': request.user.phone
    }, status=status.HTTP_200_OK)

