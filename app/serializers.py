from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import (
    User, Membership, MembershipUser, MonthlyMembershipDeposit,
    Loan, LoanInterestPayment, LoanPrinciplePayment, FundManagement, MySetting,
    PaymentTransaction, PushNotification, Popup, SupportTicket, SupportTicketReply,
    Penalty
)


class UserSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'name', 'email', 'gender', 'date_of_birth',
            'address', 'national_id', 'country_code', 'country', 
            'joined_date', 'status', 'is_staff', 
            'is_superuser', 'is_active', 'groups', 'fcm_token', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'groups']
    
    def get_groups(self, obj):
        """Return list of group names"""
        return [group.name for group in obj.groups.all()]


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = [
            'id', 'name', 'amount', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MembershipUserSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    membership = MembershipSerializer(read_only=True)
    membership_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = MembershipUser
        fields = [
            'id', 'user', 'user_id', 'membership', 'membership_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MonthlyMembershipDepositSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    membership = MembershipSerializer(read_only=True)
    membership_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = MonthlyMembershipDeposit
        fields = [
            'id', 'user', 'user_id', 'membership', 'membership_id',
            'amount', 'date', 'payment_status', 'name', 'paid_date', 'is_custom',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Auto-set date when payment_status is 'paid' and date not provided
        payment_status = validated_data.get('payment_status', 'pending')
        if payment_status == 'paid' and 'date' not in validated_data:
            from django.utils import timezone
            from app.models import MySetting
            
            settings = MySetting.get_settings()
            today = timezone.now().date()
            
            # Use configured day of month, or today's date
            if settings.membership_deposit_date:
                try:
                    # Set to the configured day of current month
                    deposit_date = today.replace(day=min(settings.membership_deposit_date, 28))
                    # If configured day has passed, use today
                    if deposit_date < today:
                        deposit_date = today
                    validated_data['date'] = deposit_date
                except ValueError:
                    # If day doesn't exist in current month (e.g., Feb 30), use today
                    validated_data['date'] = today
            else:
                validated_data['date'] = today
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Auto-update date when payment_status changes to 'paid'
        payment_status = validated_data.get('payment_status', instance.payment_status)
        
        if payment_status == 'paid' and instance.payment_status != 'paid':
            from django.utils import timezone
            from app.models import MySetting
            
            settings = MySetting.get_settings()
            today = timezone.now().date()
            
            # Only auto-set if date wasn't explicitly provided
            if 'date' not in validated_data:
                if settings.membership_deposit_date:
                    try:
                        deposit_date = today.replace(day=min(settings.membership_deposit_date, 28))
                        if deposit_date < today:
                            deposit_date = today
                        validated_data['date'] = deposit_date
                    except ValueError:
                        validated_data['date'] = today
                else:
                    validated_data['date'] = today
        
        return super().update(instance, validated_data)


class LoanInterestPaymentSerializer(serializers.ModelSerializer):
    loan_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = LoanInterestPayment
        fields = [
            'id', 'loan_id', 'amount', 'payment_status', 'paid_date', 'name', 'is_custom',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """Include loan_id in read operations"""
        representation = super().to_representation(instance)
        representation['loan_id'] = instance.loan.id
        return representation
    
    def create(self, validated_data):
        # Auto-set paid_date when payment_status is 'paid' and paid_date not provided
        payment_status = validated_data.get('payment_status', 'pending')
        if payment_status == 'paid' and 'paid_date' not in validated_data:
            from django.utils import timezone
            from app.models import MySetting
            
            settings = MySetting.get_settings()
            today = timezone.now().date()
            
            # Use configured day of month, or today's date
            if settings.loan_interest_payment_date:
                try:
                    payment_date = today.replace(day=min(settings.loan_interest_payment_date, 28))
                    if payment_date < today:
                        payment_date = today
                    validated_data['paid_date'] = payment_date
                except ValueError:
                    validated_data['paid_date'] = today
            else:
                validated_data['paid_date'] = today
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Auto-update paid_date when payment_status changes to 'paid'
        payment_status = validated_data.get('payment_status', instance.payment_status)
        
        if payment_status == 'paid' and instance.payment_status != 'paid':
            from django.utils import timezone
            from app.models import MySetting
            
            settings = MySetting.get_settings()
            today = timezone.now().date()
            
            # Only auto-set if paid_date wasn't explicitly provided
            if 'paid_date' not in validated_data:
                if settings.loan_interest_payment_date:
                    try:
                        payment_date = today.replace(day=min(settings.loan_interest_payment_date, 28))
                        if payment_date < today:
                            payment_date = today
                        validated_data['paid_date'] = payment_date
                    except ValueError:
                        validated_data['paid_date'] = today
                else:
                    validated_data['paid_date'] = today
        
        return super().update(instance, validated_data)


class LoanPrinciplePaymentSerializer(serializers.ModelSerializer):
    loan_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = LoanPrinciplePayment
        fields = [
            'id', 'loan_id', 'amount', 'payment_status', 'paid_date', 'is_custom',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """Include loan_id in read operations"""
        representation = super().to_representation(instance)
        representation['loan_id'] = instance.loan.id
        return representation
    
    def create(self, validated_data):
        # Auto-set paid_date when payment_status is 'paid' and paid_date not provided
        payment_status = validated_data.get('payment_status', 'pending')
        if payment_status == 'paid' and 'paid_date' not in validated_data:
            from django.utils import timezone
            validated_data['paid_date'] = timezone.now().date()
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Auto-update paid_date when payment_status changes to 'paid'
        payment_status = validated_data.get('payment_status', instance.payment_status)
        
        if payment_status == 'paid' and instance.payment_status != 'paid':
            from django.utils import timezone
            # Only auto-set if paid_date wasn't explicitly provided
            if 'paid_date' not in validated_data:
                validated_data['paid_date'] = timezone.now().date()
        
        return super().update(instance, validated_data)


class LoanSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    action_by = UserSerializer(read_only=True)
    action_by_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    total_paid_principle = serializers.SerializerMethodField()
    remaining_principle = serializers.SerializerMethodField()
    
    class Meta:
        model = Loan
        fields = [
            'id', 'user', 'user_id', 'applied_date', 'principal_amount',
            'interest_rate', 'total_payable', 'timeline', 'total_paid_principle',
            'remaining_principle', 'status', 'approved_date',
            'disbursed_date', 'completed_date', 'action_by', 'action_by_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_paid_principle', 'remaining_principle']
    
    def get_total_paid_principle(self, obj):
        """Calculate total paid principle from all paid principle payments"""
        return float(obj.get_total_paid_principle())
    
    def get_remaining_principle(self, obj):
        """Calculate remaining principle amount"""
        return float(obj.get_remaining_principle())


class FundManagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundManagement
        fields = [
            'id', 'type', 'amount', 'date', 'status', 'purpose',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MySettingSerializer(serializers.ModelSerializer):
    apk_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MySetting
        fields = [
            'id', 'membership_deposit_date', 'loan_interest_payment_date',
            'loan_interest_rate', 'loan_timeline', 'balance',
            'latest_app_version', 'latest_version_code', 'apk_file',
            'update_message', 'release_notes', 'mandatory_update',
            'default_penalty_amount', 'penalty_grace_period_days',
            'apk_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'apk_url']
    
    def get_apk_url(self, obj):
        """Return full URL for APK file if it exists"""
        if obj.apk_file and hasattr(obj.apk_file, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.apk_file.url)
            return obj.apk_file.url
        return None


class PaymentTransactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'payment_type', 'payment_method', 'related_object_id', 'user', 'client_txn_id',
            'order_id', 'amount', 'status', 'gateway_response', 'upi_txn_id',
            'customer_name', 'txn_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'gateway_response']


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        phone = attrs.get('phone')
        password = attrs.get('password')
        
        if phone and password:
            user = authenticate(username=phone, password=password)
            if not user:
                raise serializers.ValidationError('Invalid phone number or password.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include "phone" and "password".')
        
        return attrs


class PushNotificationSerializer(serializers.ModelSerializer):
    sent_by_name = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PushNotification
        fields = [
            'id', 'title', 'body', 'image', 'image_url', 'sent_at', 'sent_by', 
            'sent_by_name', 'is_sent', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sent_at', 'sent_by', 'created_at', 'updated_at']
    
    def get_sent_by_name(self, obj):
        """Return the name of the user who sent the notification"""
        return obj.sent_by.name if obj.sent_by else None
    
    def get_image_url(self, obj):
        """Return the full URL of the image if it exists"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class PopupSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Popup
        fields = [
            'id', 'title', 'description', 'image', 'image_url', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_image_url(self, obj):
        """Return the full URL of the image if it exists"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class SupportTicketReplySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportTicketReply
        fields = [
            'id', 'ticket', 'user', 'user_id', 'message', 'image', 'image_url',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_image_url(self, obj):
        """Return the full URL of the image if it exists"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def create(self, validated_data):
        # Auto-set user_id from request if not provided
        if 'user_id' not in validated_data or validated_data.get('user_id') is None:
            request = self.context.get('request')
            if request and request.user:
                validated_data['user_id'] = request.user.id
        return super().create(validated_data)


class SupportTicketSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)
    replies = SupportTicketReplySerializer(many=True, read_only=True)
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'user', 'user_id', 'subject', 'message', 'status',
            'replies', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Auto-set user_id from request if not provided
        if 'user_id' not in validated_data or validated_data.get('user_id') is None:
            request = self.context.get('request')
            if request and request.user:
                validated_data['user_id'] = request.user.id
        return super().create(validated_data)


class PenaltySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    total_penalty_for_payment = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    related_object = serializers.SerializerMethodField()
    
    class Meta:
        model = Penalty
        fields = [
            'id', 'user', 'penalty_type', 'related_object_id', 'related_object_type',
            'base_amount', 'month_number', 'penalty_amount', 'total_penalty',
            'total_penalty_for_payment', 'payment_status', 'due_date', 'paid_date',
            'is_overdue', 'related_object', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_penalty_for_payment', 'is_overdue']
    
    def get_total_penalty_for_payment(self, obj):
        """Get total penalty amount for the related payment"""
        return float(Penalty.get_total_for_payment(obj.penalty_type, obj.related_object_id))
    
    def get_is_overdue(self, obj):
        """Check if penalty is overdue"""
        from django.utils import timezone
        return obj.payment_status == 'pending' and timezone.now().date() > obj.due_date
    
    def get_related_object(self, obj):
        """Get related object (deposit or interest payment)"""
        from django.apps import apps
        try:
            if obj.penalty_type == 'deposit':
                Deposit = apps.get_model('app', 'MonthlyMembershipDeposit')
                deposit = Deposit.objects.filter(pk=obj.related_object_id).first()
                if deposit:
                    return {
                        'id': deposit.pk,
                        'amount': float(deposit.amount),
                        'date': deposit.date.isoformat() if deposit.date else None,
                        'payment_status': deposit.payment_status,
                        'name': deposit.name
                    }
            elif obj.penalty_type == 'interest':
                InterestPayment = apps.get_model('app', 'LoanInterestPayment')
                payment = InterestPayment.objects.filter(pk=obj.related_object_id).first()
                if payment:
                    return {
                        'id': payment.pk,
                        'amount': float(payment.amount),
                        'paid_date': payment.paid_date.isoformat() if payment.paid_date else None,
                        'payment_status': payment.payment_status,
                        'name': payment.name,
                        'loan_id': payment.loan_id
                    }
        except (LookupError, AttributeError):
            pass
        return None
