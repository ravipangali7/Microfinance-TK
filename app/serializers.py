from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import (
    User, Membership, MembershipUser, MonthlyMembershipDeposit,
    Loan, LoanInterestPayment, LoanPrinciplePayment, OrganizationalWithdrawal, MySetting,
    PaymentTransaction
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
            'amount', 'date', 'payment_status', 'name', 'paid_date',
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
            'id', 'loan_id', 'amount', 'payment_status', 'paid_date', 'name',
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
            'id', 'loan_id', 'amount', 'payment_status', 'paid_date',
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


class OrganizationalWithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationalWithdrawal
        fields = [
            'id', 'amount', 'date', 'status', 'purpose',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MySettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MySetting
        fields = [
            'id', 'membership_deposit_date', 'loan_interest_payment_date',
            'loan_interest_rate', 'loan_timeline', 'balance',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentTransactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'payment_type', 'related_object_id', 'user', 'client_txn_id',
            'order_id', 'amount', 'status', 'gateway_response', 'upi_txn_id',
            'txn_date', 'created_at', 'updated_at'
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
