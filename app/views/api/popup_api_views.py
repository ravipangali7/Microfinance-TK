from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from app.models import Popup
from app.serializers import PopupSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_popup_api(request):
    """API endpoint to get the active popup"""
    try:
        popup = Popup.objects.filter(is_active=True).order_by('-created_at').first()
        
        if popup:
            serializer = PopupSerializer(popup, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'No active popup found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

