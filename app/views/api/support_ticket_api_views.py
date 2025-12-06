from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from app.models import SupportTicket, SupportTicketReply, SupportTicketStatus
from app.serializers import SupportTicketSerializer, SupportTicketReplySerializer
from app.views.admin.filter_helpers import (
    apply_text_search, apply_date_filter, parse_date_range
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def support_ticket_list_api(request):
    """API endpoint to list user's support tickets"""
    try:
        tickets = SupportTicket.objects.filter(user=request.user)
        
        # Apply search filter
        search = request.query_params.get('search', '').strip()
        if search:
            tickets = apply_text_search(tickets, search, ['subject', 'message', 'user__name'])
        
        # Apply status filter
        status_filter = request.query_params.get('status', '').strip()
        if status_filter:
            tickets = tickets.filter(status=status_filter)
        
        # Apply date range filter
        date_range_str = request.query_params.get('date_range', '').strip()
        if date_range_str:
            date_range = parse_date_range(date_range_str)
            if date_range:
                start_date, end_date = date_range
                tickets = apply_date_filter(tickets, 'created_at', start_date, end_date)
        
        tickets = tickets.order_by('-created_at')
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

