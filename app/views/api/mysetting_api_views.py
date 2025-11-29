from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from app.models import MySetting
from app.serializers import MySettingSerializer
from app.views.admin.helpers import is_admin


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mysetting_detail_api(request):
    """Get system settings - accessible to all authenticated users (read-only)"""
    # Allow all authenticated users to view settings
    # This allows members to calculate "My Share" = system_balance / total_users
    settings = MySetting.get_settings()
    serializer = MySettingSerializer(settings)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def loan_settings_api(request):
    """Get loan-related settings (interest rate and timeline) - accessible to all authenticated users"""
    settings = MySetting.get_settings()
    # Return only loan-related settings, exclude balance
    return Response({
        'loan_interest_rate': str(settings.loan_interest_rate),
        'loan_timeline': settings.loan_timeline,
    }, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def mysetting_update_api(request):
    """Update system settings"""
    # Only Admin can update settings
    if not is_admin(request.user):
        return Response(
            {'error': 'Access denied. Only Admin can update settings.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    settings = MySetting.get_settings()
    serializer = MySettingSerializer(settings, data=request.data, partial=True)
    if serializer.is_valid():
        settings = serializer.save()
        return Response(MySettingSerializer(settings).data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

