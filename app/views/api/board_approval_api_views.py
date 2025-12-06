from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from app.models import Loan, FundManagement, LoanStatus, WithdrawalStatus
from app.serializers import LoanSerializer, FundManagementSerializer
from app.views.admin.helpers import is_admin_or_board


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def board_approval_list_api(request):
    """Get pending loans and fund management records for board approval"""
    # Only Admin and Board can access
    if not is_admin_or_board(request.user):
        return Response(
            {'error': 'Access denied. Only Admin and Board members can access this page.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get pending loans
    pending_loans = Loan.objects.filter(status=LoanStatus.PENDING).select_related('user').order_by('-applied_date', '-created_at')
    loans_serializer = LoanSerializer(pending_loans, many=True)
    
    # Get pending fund management records
    pending_fund_management = FundManagement.objects.filter(status=WithdrawalStatus.PENDING).order_by('-date', '-created_at')
    fund_management_serializer = FundManagementSerializer(pending_fund_management, many=True)
    
    return Response({
        'pending_loans': loans_serializer.data,
        'pending_fund_management': fund_management_serializer.data,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_loan_api(request, pk):
    """Approve a loan"""
    if not is_admin_or_board(request.user):
        return Response(
            {'error': 'Access denied. Only Admin and Board members can approve loans.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    loan = get_object_or_404(Loan, pk=pk, status=LoanStatus.PENDING)
    loan.status = LoanStatus.APPROVED
    loan.action_by = request.user
    loan.approved_date = timezone.now().date()
    loan.save()
    
    serializer = LoanSerializer(loan)
    return Response({
        'message': f'Loan #{loan.id} has been approved successfully.',
        'loan': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_loan_api(request, pk):
    """Reject a loan"""
    if not is_admin_or_board(request.user):
        return Response(
            {'error': 'Access denied. Only Admin and Board members can reject loans.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    loan = get_object_or_404(Loan, pk=pk, status=LoanStatus.PENDING)
    loan.status = LoanStatus.REJECTED
    loan.action_by = request.user
    loan.save()
    
    serializer = LoanSerializer(loan)
    return Response({
        'message': f'Loan #{loan.id} has been rejected.',
        'loan': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_loan_status_api(request, pk):
    """Update loan status"""
    if not is_admin_or_board(request.user):
        return Response(
            {'error': 'Access denied. Only Admin and Board members can update loan status.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    loan = get_object_or_404(Loan, pk=pk)
    new_status = request.data.get('status')
    
    if not new_status or new_status not in [choice[0] for choice in LoanStatus.choices]:
        return Response(
            {'error': 'Invalid status provided.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    old_status = loan.status
    loan.status = new_status
    loan.action_by = request.user
    
    # Set dates based on status
    if new_status == LoanStatus.APPROVED and old_status != LoanStatus.APPROVED:
        loan.approved_date = timezone.now().date()
    elif new_status == LoanStatus.ACTIVE and old_status != LoanStatus.ACTIVE:
        loan.disbursed_date = timezone.now().date()
    elif new_status == LoanStatus.COMPLETED and old_status != LoanStatus.COMPLETED:
        loan.completed_date = timezone.now().date()
    
    loan.save()
    
    serializer = LoanSerializer(loan)
    return Response({
        'message': f'Loan #{loan.id} status updated to {loan.get_status_display()} successfully.',
        'loan': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_fund_management_api(request, pk):
    """Approve a fund management record"""
    if not is_admin_or_board(request.user):
        return Response(
            {'error': 'Access denied. Only Admin and Board members can approve fund management records.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    fund_management = get_object_or_404(FundManagement, pk=pk, status=WithdrawalStatus.PENDING)
    fund_management.status = WithdrawalStatus.APPROVED
    fund_management.save()
    
    serializer = FundManagementSerializer(fund_management)
    return Response({
        'message': f'Fund Management #{fund_management.id} has been approved successfully.',
        'fund_management': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_fund_management_api(request, pk):
    """Reject a fund management record"""
    if not is_admin_or_board(request.user):
        return Response(
            {'error': 'Access denied. Only Admin and Board members can reject fund management records.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    fund_management = get_object_or_404(FundManagement, pk=pk, status=WithdrawalStatus.PENDING)
    fund_management.status = WithdrawalStatus.REJECTED
    fund_management.save()
    
    serializer = FundManagementSerializer(fund_management)
    return Response({
        'message': f'Fund Management #{fund_management.id} has been rejected.',
        'fund_management': serializer.data
    }, status=status.HTTP_200_OK)

