from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from app.models import SupportTicket, SupportTicketReply
from app.serializers import SupportTicketSerializer, SupportTicketReplySerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def support_ticket_list_api(request):
    """API endpoint to list user's support tickets"""
    try:
        tickets = SupportTicket.objects.filter(user=request.user).order_by('-created_at')
        serializer = SupportTicketSerializer(tickets, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def support_ticket_create_api(request):
    """API endpoint to create a new support ticket"""
    try:
        data = request.data.copy()
        data['user_id'] = request.user.id
        
        serializer = SupportTicketSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            ticket = serializer.save()
            return Response(
                SupportTicketSerializer(ticket, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def support_ticket_detail_api(request, pk):
    """API endpoint to get ticket details with replies"""
    try:
        ticket = SupportTicket.objects.get(pk=pk, user=request.user)
        serializer = SupportTicketSerializer(ticket, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    except SupportTicket.DoesNotExist:
        return Response(
            {'error': 'Ticket not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def support_ticket_reply_api(request, pk):
    """API endpoint to add a reply to a support ticket with optional image upload"""
    try:
        ticket = SupportTicket.objects.get(pk=pk, user=request.user)
        
        # Handle multipart form data
        data = {}
        if request.FILES:
            # If image is uploaded via multipart
            if 'image' in request.FILES:
                data['image'] = request.FILES['image']
        if request.data:
            # Get text fields from request.data
            if 'message' in request.data:
                data['message'] = request.data['message']
        
        data['ticket'] = ticket.id
        data['user_id'] = request.user.id
        
        serializer = SupportTicketReplySerializer(data=data, context={'request': request})
        if serializer.is_valid():
            reply = serializer.save()
            return Response(
                SupportTicketReplySerializer(reply, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except SupportTicket.DoesNotExist:
        return Response(
            {'error': 'Ticket not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

