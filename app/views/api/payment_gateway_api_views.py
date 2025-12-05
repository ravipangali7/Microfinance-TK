from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
from django.db import IntegrityError
from datetime import datetime, timedelta
from urllib.parse import unquote, urlparse, parse_qs
from app.models import (
    PaymentTransaction, MonthlyMembershipDeposit, 
    LoanInterestPayment, LoanPrinciplePayment, User
)
from app.services.payment_gateway_service import PaymentGatewayService
from decimal import Decimal
import traceback


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_order_api(request):
    """
    Create payment order with UPI gateway
    
    Request body:
    {
        "payment_type": "deposit", "interest", or "principle",
        "payment_id": <id of deposit, interest payment, or principle payment>,
        "amount": <amount>
    }
    """
    payment_type = request.data.get('payment_type')
    payment_id = request.data.get('payment_id')
    amount = request.data.get('amount')
    
    # Validate inputs
    if not payment_type or payment_type not in ['deposit', 'interest', 'principle']:
        return Response(
            {'error': 'Invalid payment_type. Must be "deposit", "interest", or "principle".'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not payment_id:
        return Response(
            {'error': 'payment_id is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not amount:
        return Response(
            {'error': 'amount is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        amount_decimal = Decimal(str(amount))
    except:
        return Response(
            {'error': 'Invalid amount format.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get the payment object
    if payment_type == 'deposit':
        payment_obj = get_object_or_404(MonthlyMembershipDeposit, pk=payment_id)
        # Verify user owns this deposit
        if payment_obj.user.id != request.user.id:
            return Response(
                {'error': 'You can only create payment orders for your own deposits.'},
                status=status.HTTP_403_FORBIDDEN
            )
    elif payment_type == 'interest':
        payment_obj = get_object_or_404(LoanInterestPayment, pk=payment_id)
        # Verify user owns this loan
        if payment_obj.loan.user.id != request.user.id:
            return Response(
                {'error': 'You can only create payment orders for your own loan payments.'},
                status=status.HTTP_403_FORBIDDEN
            )
    else:  # principle
        payment_obj = get_object_or_404(LoanPrinciplePayment, pk=payment_id)
        # Verify user owns this loan
        if payment_obj.loan.user.id != request.user.id:
            return Response(
                {'error': 'You can only create payment orders for your own loan payments.'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Check if payment is already paid
    if payment_obj.payment_status == 'paid':
        return Response(
            {'error': 'This payment has already been completed.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Note: We no longer create pending PaymentTransaction records
    # Transaction will be created only when payment is successful
    
    # Validate user fields before processing
    if not request.user.name:
        print(f"[ERROR] create_payment_order_api: User {request.user.id} missing name field")
        return Response(
            {'error': 'User profile is incomplete. Please update your name.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not request.user.phone:
        print(f"[ERROR] create_payment_order_api: User {request.user.id} missing phone field")
        return Response(
            {'error': 'User profile is incomplete. Please update your phone number.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Generate redirect URL
    redirect_url = f"{settings.UPI_PAYMENT_REDIRECT_URL_BASE}/api/payment/callback/"
    
    # Create payment order
    try:
        order_result = PaymentGatewayService.create_payment_order(
            payment_type=payment_type,
            payment_id=payment_id,
            user=request.user,
            amount=amount_decimal,
            redirect_url=redirect_url
        )
    except Exception as e:
        print(f"[ERROR] create_payment_order_api: Exception in PaymentGatewayService.create_payment_order")
        print(f"[ERROR] User ID: {request.user.id}, Payment Type: {payment_type}, Payment ID: {payment_id}")
        print(f"[ERROR] Exception: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return Response(
            {'error': 'Failed to create payment order. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    if not order_result.get('success'):
        error_msg = order_result.get('error', 'Failed to create payment order')
        print(f"[ERROR] create_payment_order_api: Payment gateway returned error")
        print(f"[ERROR] User ID: {request.user.id}, Payment Type: {payment_type}, Payment ID: {payment_id}")
        print(f"[ERROR] Gateway Error: {error_msg}")
        return Response(
            {'error': error_msg},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Note: We do NOT create PaymentTransaction here - it will be created only when payment is successful
    # Return payment order details for user to proceed with payment
    print(f"[INFO] create_payment_order_api: Payment order created successfully, client_txn_id: {order_result['client_txn_id']}")
    return Response({
        'success': True,
        'client_txn_id': order_result['client_txn_id'],
        'order_id': order_result.get('order_id'),
        'payment_url': order_result.get('payment_url'),
        'upi_intent': order_result.get('upi_intent', {}),
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_payment_status_api(request):
    """
    Check payment status from gateway
    
    Request body:
    {
        "client_txn_id": "<client transaction id>",
        "txn_date": "DD-MM-YYYY" (optional)
    }
    """
    client_txn_id = request.data.get('client_txn_id')
    txn_date = request.data.get('txn_date')
    
    if not client_txn_id:
        return Response(
            {'error': 'client_txn_id is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Parse client_txn_id to get payment_type and payment_id
    # Format: {payment_type}_{payment_id}_{timestamp}
    try:
        parts = client_txn_id.split('_')
        if len(parts) >= 3:
            payment_type = parts[0]  # deposit, interest, or principle
            payment_id = int(parts[1])
        else:
            raise ValueError("Invalid client_txn_id format")
    except (ValueError, IndexError) as e:
        return Response(
            {'error': 'Invalid client_txn_id format.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify user owns this payment
    if payment_type == 'deposit':
        payment_obj = get_object_or_404(MonthlyMembershipDeposit, pk=payment_id)
        if payment_obj.user.id != request.user.id:
            return Response(
                {'error': 'Access denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
    elif payment_type == 'interest':
        payment_obj = get_object_or_404(LoanInterestPayment, pk=payment_id)
        if payment_obj.loan.user.id != request.user.id:
            return Response(
                {'error': 'Access denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
    else:  # principle
        payment_obj = get_object_or_404(LoanPrinciplePayment, pk=payment_id)
        if payment_obj.loan.user.id != request.user.id:
            return Response(
                {'error': 'Access denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Check status from gateway
    status_result = PaymentGatewayService.check_payment_status(
        client_txn_id=client_txn_id,
        txn_date=txn_date
    )
    
    if not status_result.get('success'):
        return Response({
            'success': False,
            'status': 'unknown',
            'error': status_result.get('error', 'Failed to check payment status'),
        }, status=status.HTTP_200_OK)
    
    # Create PaymentTransaction only if payment is successful
    gateway_status = status_result.get('status', '').lower()
    payment_transaction = None
    
    if gateway_status == 'success':
        # Check if transaction already exists
        try:
            payment_transaction = PaymentTransaction.objects.get(client_txn_id=client_txn_id)
            # Update existing transaction
            PaymentGatewayService.update_payment_status(payment_transaction, status_result)
            payment_transaction.refresh_from_db()
        except PaymentTransaction.DoesNotExist:
            # Create new transaction on success
            payment_transaction = PaymentGatewayService.create_payment_transaction_on_success(
                client_txn_id=client_txn_id,
                payment_type=payment_type,
                payment_id=payment_id,
                status_response=status_result
            )
    
    return Response({
        'success': True,
        'status': gateway_status,
        'transaction_status': payment_transaction.status if payment_transaction else gateway_status,
        'transaction_id': payment_transaction.id if payment_transaction else None,
        'order_id': status_result.get('order_id'),
        'upi_txn_id': status_result.get('upi_txn_id'),
        'amount': float(status_result.get('amount', 0)),
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([])  # No authentication required for callback
def payment_callback_api(request):
    """
    Payment callback endpoint for redirect_url
    This is called by the payment gateway after payment
    """
    # Enhanced logging for debugging
    request_url = request.build_absolute_uri()
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    client_ip = request.META.get('REMOTE_ADDR', 'Unknown')
    
    # Extract client_txn_id more robustly from malformed URLs
    # URL might be: /api/payment/callback/?client_txn_id=deposit_27_1764698377?client_txn_id=deposit_27_1764698377&txn_id=144353224
    # We need to extract the FIRST client_txn_id value before any embedded query strings
    
    raw_client_txn_id = None
    
    # Method 1: Extract from raw URL string before parsing (most reliable for malformed URLs)
    if 'client_txn_id=' in request_url:
        # Find the first occurrence of client_txn_id=
        start_idx = request_url.find('client_txn_id=')
        if start_idx != -1:
            # Extract from 'client_txn_id=' to the next '&' or end of string
            value_start = start_idx + len('client_txn_id=')
            # Find the end - look for '&' (not '?' as it might be in the value itself)
            end_idx = request_url.find('&', value_start)
            if end_idx == -1:
                end_idx = len(request_url)
            raw_client_txn_id = request_url[value_start:end_idx]
    
    # Method 2: Fallback to standard parsing
    if not raw_client_txn_id:
        parsed_url = urlparse(request_url)
        query_params = parse_qs(parsed_url.query)
        if 'client_txn_id' in query_params:
            # parse_qs returns a list, get first value
            raw_client_txn_id = query_params['client_txn_id'][0] if query_params['client_txn_id'] else None
    
    # Method 3: Fallback to request.GET or request.data
    if not raw_client_txn_id:
        raw_client_txn_id = request.GET.get('client_txn_id') or request.data.get('client_txn_id')
    
    if not raw_client_txn_id:
        print(f"[ERROR] payment_callback_api: No client_txn_id provided")
        print(f"[ERROR] Request URL: {request_url}")
        print(f"[ERROR] User Agent: {user_agent}, IP: {client_ip}")
        return Response(
            '<html><body><h1>Payment Error</h1><p>Invalid callback parameters. No transaction ID provided.</p></body></html>',
            content_type='text/html',
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Clean the client_txn_id - remove any embedded query strings
    # Handle cases like: "deposit_27_1764698377?client_txn_id=deposit_27_1764698377"
    # Split on '?' and '&' to take the first part
    cleaned_raw_id = raw_client_txn_id.split('?')[0].split('&')[0].strip()
    
    # URL-decode the cleaned client_txn_id
    try:
        client_txn_id = unquote(cleaned_raw_id)
    except Exception as e:
        print(f"[ERROR] payment_callback_api: Failed to decode client_txn_id: {e}")
        client_txn_id = cleaned_raw_id  # Use cleaned raw value as fallback
    
    # Log received parameters
    print(f"[INFO] payment_callback_api: Received callback")
    print(f"[INFO] Request URL: {request_url}")
    print(f"[INFO] Raw client_txn_id: {raw_client_txn_id}")
    print(f"[INFO] Cleaned client_txn_id: {cleaned_raw_id}")
    print(f"[INFO] Decoded client_txn_id: {client_txn_id}")
    print(f"[INFO] User Agent: {user_agent}, IP: {client_ip}")
    
    # Parse client_txn_id to get payment_type and payment_id
    # Format: {payment_type}_{payment_id}_{timestamp}
    try:
        parts = client_txn_id.split('_')
        if len(parts) >= 3:
            payment_type = parts[0]  # deposit, interest, or principle
            payment_id = int(parts[1])
        else:
            raise ValueError("Invalid client_txn_id format")
    except (ValueError, IndexError) as e:
        print(f"[ERROR] payment_callback_api: Failed to parse client_txn_id: {e}")
        error_html = f'''
        <html>
        <body>
            <h1>Payment Error</h1>
            <p>Invalid transaction ID format.</p>
            <p><strong>Received Transaction ID:</strong> {client_txn_id}</p>
            <p>Please contact support if you believe this is an error.</p>
        </body>
        </html>
        '''
        return Response(
            error_html,
            content_type='text/html',
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check payment status from gateway
    txn_date = timezone.now().strftime('%d-%m-%Y')
    status_result = PaymentGatewayService.check_payment_status(
        client_txn_id=client_txn_id,
        txn_date=txn_date
    )
    
    # Create PaymentTransaction only if payment is successful
    payment_transaction = None
    if status_result.get('success'):
        gateway_status = status_result.get('status', '').lower()
        if gateway_status == 'success':
            # Check if transaction already exists
            try:
                payment_transaction = PaymentTransaction.objects.get(client_txn_id=client_txn_id)
                # Update existing transaction
                PaymentGatewayService.update_payment_status(payment_transaction, status_result)
                payment_transaction.refresh_from_db()
            except PaymentTransaction.DoesNotExist:
                # Create PaymentTransaction and update related payment object
                payment_transaction = PaymentGatewayService.create_payment_transaction_on_success(
                    client_txn_id=client_txn_id,
                    payment_type=payment_type,
                    payment_id=payment_id,
                    status_response=status_result
                )
    
    # Return HTML page with result
    if payment_transaction and payment_transaction.status == 'success':
        # Create deep link to redirect to Flutter app with transaction ID
        # Also include transaction_id in the page URL for WebView detection
        deep_link = f"microfinance://payment/success?transaction_id={payment_transaction.id}&client_txn_id={payment_transaction.client_txn_id}"
        
        # Add transaction_id to the current URL for WebView to extract
        success_url = f"{request_url.split('?')[0]}?transaction_id={payment_transaction.id}&client_txn_id={payment_transaction.client_txn_id}&status=success"
        
        html = f'''
        <html>
        <head>
            <title>Payment Success</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #10B981 0%, #059669 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 400px;
                }}
                .success-icon {{
                    font-size: 64px;
                    color: #10B981;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #10B981;
                    margin: 0 0 10px 0;
                }}
                p {{
                    color: #6B7280;
                    margin: 10px 0;
                }}
            </style>
            <script>
                // Try to redirect to Flutter app using deep link
                function redirectToApp() {{
                    const deepLink = "{deep_link}";
                    // Try deep link first
                    window.location.href = deepLink;
                    
                    // Fallback: If deep link doesn't work, try after a short delay
                    setTimeout(function() {{
                        // If still on this page, try alternative redirect
                        if (document.visibilityState === 'visible') {{
                            // Try using intent URL for Android
                            window.location.href = "intent://payment/success?transaction_id={payment_transaction.id}#Intent;scheme=microfinance;package=com.microfinance.app;end";
                        }}
                    }}, 500);
                }}
                
                // Auto-redirect on page load
                window.onload = function() {{
                    redirectToApp();
                }};
                
                // Also update the URL to include transaction_id for WebView detection
                if (window.history && window.history.replaceState) {{
                    const newUrl = "{success_url}";
                    window.history.replaceState({{}}, '', newUrl);
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✓</div>
                <h1>Payment Successful!</h1>
                <p>Your payment has been processed successfully.</p>
                <p>Transaction ID: {payment_transaction.client_txn_id}</p>
                <p>Redirecting to app...</p>
                <p style="font-size: 12px; color: #9CA3AF;">If you are not redirected, <a href="{deep_link}">click here</a></p>
            </div>
        </body>
        </html>
        '''
    else:
        # Payment is pending or failed - no transaction created
        html = f'''
        <html>
        <head>
            <title>Payment Status</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 400px;
                }}
                .pending-icon {{
                    font-size: 64px;
                    color: #F59E0B;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #F59E0B;
                    margin: 0 0 10px 0;
                }}
                p {{
                    color: #6B7280;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="pending-icon">⏳</div>
                <h1>Payment Pending</h1>
                <p>Your payment is being processed.</p>
                <p>Transaction ID: {client_txn_id}</p>
                <p>Please check back in a few moments or return to the app.</p>
            </div>
        </body>
        </html>
        '''
    
    return Response(html, content_type='text/html', status=status.HTTP_200_OK)

