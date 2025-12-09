from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from decimal import Decimal
from app.models import Penalty, PaymentStatus, PenaltyType
from app.serializers import PenaltySerializer
from app.views.admin.helpers import is_admin_board_or_staff, is_member
from app.views.admin.filter_helpers import (
    apply_text_search, apply_date_filter, apply_amount_range_filter, parse_date_range
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def penalty_list_api(request):
    """List penalties - all users see only their own penalties"""
    # Always filter by logged-in user
    penalties = Penalty.objects.filter(user=request.user).select_related('user')
    
    # Apply search filter
    search = request.query_params.get('search', '').strip()
    if search:
        penalties = apply_text_search(penalties, search, ['user__name', 'user__phone'])
    
    # Apply penalty type filter
    penalty_type = request.query_params.get('penalty_type', '').strip()
    if penalty_type:
        penalties = penalties.filter(penalty_type=penalty_type)
    
    # Apply status filter
    status_filter = request.query_params.get('status', '').strip()
    if status_filter:
        penalties = penalties.filter(payment_status=status_filter)
    
    # Apply date range filter
    date_range_str = request.query_params.get('date_range', '').strip()
    if date_range_str:
        date_range = parse_date_range(date_range_str)
        if date_range:
            start_date, end_date = date_range
            penalties = apply_date_filter(penalties, 'due_date', start_date, end_date)
    
    # Apply amount range filter
    min_amount = request.query_params.get('min_amount', '').strip()
    max_amount = request.query_params.get('max_amount', '').strip()
    if min_amount or max_amount:
        penalties = apply_amount_range_filter(penalties, 'penalty_amount', min_amount, max_amount)
    
    penalties = penalties.order_by('-due_date', '-created_at')
    serializer = PenaltySerializer(penalties, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def penalty_detail_api(request, pk):
    """Get penalty details - all users can only see their own penalties"""
    penalty = get_object_or_404(Penalty, pk=pk)
    
    # All users can only see their own penalties
    if penalty.user.id != request.user.id:
        return Response(
            {'error': 'Access denied. You can only view your own penalties.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = PenaltySerializer(penalty, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def penalty_summary_api(request):
    """Get penalty summary - all users see only their own penalties"""
    penalty_type = request.query_params.get('penalty_type')
    related_object_id = request.query_params.get('related_object_id')
    
    # Build query - always filter by logged-in user
    query = Penalty.objects.filter(
        payment_status=PaymentStatus.PENDING,
        user=request.user
    )
    
    if penalty_type:
        query = query.filter(penalty_type=penalty_type)
    
    if related_object_id:
        try:
            query = query.filter(related_object_id=int(related_object_id))
        except ValueError:
            pass
    
    # Calculate totals
    total_count = query.count()
    total_amount = sum(penalty.penalty_amount for penalty in query)
    
    # Group by penalty type
    by_type = {}
    for penalty_type_choice in PenaltyType.choices:
        type_penalties = query.filter(penalty_type=penalty_type_choice[0])
        by_type[penalty_type_choice[0]] = {
            'count': type_penalties.count(),
            'amount': float(sum(p.penalty_amount for p in type_penalties))
        }
    
    return Response({
        'total_count': total_count,
        'total_amount': float(total_amount),
        'by_type': by_type
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def penalty_mark_paid_api(request, pk):
    """Mark penalty as paid (admin only)"""
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can mark penalties as paid.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    penalty = get_object_or_404(Penalty, pk=pk)
    
    # Update penalty status
    penalty.payment_status = PaymentStatus.PAID
    if not penalty.paid_date:
        from django.utils import timezone
        penalty.paid_date = timezone.now().date()
    penalty.save()
    
    serializer = PenaltySerializer(penalty, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def penalty_adjust_api(request, pk):
    """Adjust penalty amount (admin only)"""
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can adjust penalties.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    penalty = get_object_or_404(Penalty, pk=pk)
    
    # Get adjustment data
    new_amount = request.data.get('penalty_amount')
    if new_amount is not None:
        try:
            penalty.penalty_amount = Decimal(str(new_amount))
            penalty.save()
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid penalty amount.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Update payment status if provided
    payment_status = request.data.get('payment_status')
    if payment_status in [PaymentStatus.PENDING, PaymentStatus.PAID]:
        penalty.payment_status = payment_status
        if payment_status == PaymentStatus.PAID and not penalty.paid_date:
            from django.utils import timezone
            penalty.paid_date = timezone.now().date()
        penalty.save()
    
    serializer = PenaltySerializer(penalty, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)

