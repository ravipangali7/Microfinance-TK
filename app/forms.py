from django import forms
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import (
    User, Membership, MembershipUser, MonthlyMembershipDeposit,
    Loan, LoanInterestPayment, LoanPrinciplePayment, OrganizationalWithdrawal, MySetting,
    UserStatus, LoanStatus, PaymentStatus, WithdrawalStatus, Gender, PushNotification, Popup
)


class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text='Leave blank to keep current password'
    )
    
    class Meta:
        model = User
        fields = [
            'phone', 'name', 'email', 'password', 'gender', 'date_of_birth',
            'address', 'national_id', 'country_code', 'country', 'joined_date',
            'status', 'is_staff', 'is_superuser', 'is_active'
        ]
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}, choices=Gender.choices),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'national_id': forms.TextInput(attrs={'class': 'form-control'}),
            'country_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'joined_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}, choices=UserStatus.choices),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        is_new = user.pk is None
        
        if password:
            user.set_password(password)
        if commit:
            user.save()
            # Assign "Member" group to new users if they have no groups
            if is_new and user.groups.count() == 0:
                try:
                    member_group = Group.objects.get(name='Member')
                    user.groups.add(member_group)
                except Group.DoesNotExist:
                    # If Member group doesn't exist, create it
                    member_group = Group.objects.create(name='Member')
                    user.groups.add(member_group)
        return user


class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = ['name', 'amount']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class MembershipUserForm(forms.ModelForm):
    membership = forms.ModelChoiceField(
        queryset=Membership.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    user = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = MembershipUser
        fields = ['membership', 'user']


class MonthlyMembershipDepositForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    membership = forms.ModelChoiceField(
        queryset=Membership.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_custom = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    class Meta:
        model = MonthlyMembershipDeposit
        fields = ['user', 'membership', 'amount', 'date', 'payment_status', 'is_custom']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}, choices=PaymentStatus.choices),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure is_custom defaults to False if not provided
        if 'is_custom' not in self.data and not self.instance.pk:
            self.fields['is_custom'].initial = False
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Explicitly set is_custom to False if not provided
        if not hasattr(instance, 'is_custom') or instance.is_custom is None:
            instance.is_custom = False
        if commit:
            instance.save()
        return instance


class LoanForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    action_by = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('name'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Loan
        fields = [
            'user', 'applied_date', 'principal_amount', 'interest_rate',
            'total_payable', 'timeline',
            'status', 'approved_date', 'disbursed_date', 'completed_date', 'action_by'
        ]
        widgets = {
            'applied_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'principal_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_payable': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'timeline': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}, choices=LoanStatus.choices),
            'approved_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'disbursed_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'completed_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class LoanCreateForm(forms.ModelForm):
    """Simplified form for loan creation - only user input fields"""
    user = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Loan
        fields = ['user', 'applied_date', 'principal_amount', 'timeline']
        widgets = {
            'applied_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'principal_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'timeline': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default timeline from MySetting
        try:
            settings = MySetting.get_settings()
            self.fields['timeline'].initial = settings.loan_timeline
        except:
            self.fields['timeline'].initial = 12
    
    def clean(self):
        cleaned_data = super().clean()
        principal_amount = cleaned_data.get('principal_amount')
        timeline = cleaned_data.get('timeline')
        
        if principal_amount and principal_amount <= 0:
            raise forms.ValidationError({
                'principal_amount': 'Principal amount must be greater than zero.'
            })
        
        if timeline and timeline <= 0:
            raise forms.ValidationError({
                'timeline': 'Timeline must be greater than zero.'
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Override save to set auto-calculated fields"""
        instance = super().save(commit=False)
        principal_amount = instance.principal_amount
        timeline = instance.timeline
        is_new = instance.pk is None
        
        # Get settings for default values
        try:
            settings = MySetting.get_settings()
            if not instance.interest_rate:
                instance.interest_rate = settings.loan_interest_rate
            if not instance.timeline:
                instance.timeline = settings.loan_timeline
        except:
            if not instance.interest_rate:
                instance.interest_rate = Decimal('10.00')
            if not instance.timeline:
                instance.timeline = 12
        
        # Auto-calculate total_payable: principal + (principal * interest_rate / 100)
        if principal_amount and instance.interest_rate:
            interest_amount = (principal_amount * instance.interest_rate) / Decimal('100')
            instance.total_payable = principal_amount + interest_amount
        
        # Set default status to PENDING only for new instances
        if is_new:
            instance.status = LoanStatus.PENDING
        
        if commit:
            instance.save()
        
        return instance


class LoanInterestPaymentForm(forms.ModelForm):
    loan = forms.ModelChoiceField(
        queryset=Loan.objects.filter(status__in=[LoanStatus.APPROVED, LoanStatus.ACTIVE]).select_related('user').order_by('-applied_date'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_custom = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    class Meta:
        model = LoanInterestPayment
        fields = ['loan', 'amount', 'payment_status', 'paid_date', 'is_custom']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}, choices=PaymentStatus.choices),
            'paid_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default paid_date to today for new instances only
        if not self.instance.pk and 'paid_date' in self.fields:
            from django.utils import timezone
            today = timezone.now().date()
            self.fields['paid_date'].initial = today
        # Ensure is_custom defaults to False if not provided
        if 'is_custom' not in self.data and not self.instance.pk:
            self.fields['is_custom'].initial = False
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Explicitly set is_custom to False if not provided
        if not hasattr(instance, 'is_custom') or instance.is_custom is None:
            instance.is_custom = False
        if commit:
            instance.save()
        return instance


class LoanPrinciplePaymentForm(forms.ModelForm):
    loan = forms.ModelChoiceField(
        queryset=Loan.objects.filter(status__in=[LoanStatus.APPROVED, LoanStatus.ACTIVE]).select_related('user').order_by('-applied_date'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_custom = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    class Meta:
        model = LoanPrinciplePayment
        fields = ['loan', 'amount', 'payment_status', 'paid_date', 'is_custom']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}, choices=PaymentStatus.choices),
            'paid_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default paid_date to today for new instances only
        if not self.instance.pk and 'paid_date' in self.fields:
            from django.utils import timezone
            today = timezone.now().date()
            self.fields['paid_date'].initial = today
        # Ensure is_custom defaults to False if not provided
        if 'is_custom' not in self.data and not self.instance.pk:
            self.fields['is_custom'].initial = False
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Explicitly set is_custom to False if not provided
        if not hasattr(instance, 'is_custom') or instance.is_custom is None:
            instance.is_custom = False
        if commit:
            instance.save()
        return instance


class OrganizationalWithdrawalForm(forms.ModelForm):
    class Meta:
        model = OrganizationalWithdrawal
        fields = ['amount', 'date', 'status', 'purpose']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}, choices=WithdrawalStatus.choices),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        
        if amount and amount <= 0:
            raise forms.ValidationError({
                'amount': 'Withdrawal amount must be greater than zero.'
            })
        
        return cleaned_data


class OrganizationalWithdrawalCreateForm(forms.ModelForm):
    """Simplified form for organizational withdrawal creation"""
    class Meta:
        model = OrganizationalWithdrawal
        fields = ['amount', 'date', 'purpose']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        
        if amount and amount <= 0:
            raise forms.ValidationError({
                'amount': 'Withdrawal amount must be greater than zero.'
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Override save to set default status to PENDING"""
        instance = super().save(commit=False)
        instance.status = WithdrawalStatus.PENDING
        if commit:
            instance.save()
        return instance


class MySettingForm(forms.ModelForm):
    class Meta:
        model = MySetting
        fields = [
            'membership_deposit_date', 'loan_interest_payment_date',
            'loan_interest_rate', 'loan_timeline', 'balance',
            'latest_app_version', 'latest_version_code', 'apk_file',
            'update_message', 'release_notes', 'mandatory_update'
        ]
        widgets = {
            'membership_deposit_date': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
            'loan_interest_payment_date': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
            'loan_interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'loan_timeline': forms.NumberInput(attrs={'class': 'form-control'}),
            'balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'latest_app_version': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1.0.1'}),
            'latest_version_code': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'apk_file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.apk'}),
            'update_message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'release_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'mandatory_update': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        membership_deposit_date = cleaned_data.get('membership_deposit_date')
        loan_interest_payment_date = cleaned_data.get('loan_interest_payment_date')
        
        if membership_deposit_date and (membership_deposit_date < 1 or membership_deposit_date > 31):
            raise forms.ValidationError({
                'membership_deposit_date': 'Day of month must be between 1 and 31.'
            })
        
        if loan_interest_payment_date and (loan_interest_payment_date < 1 or loan_interest_payment_date > 31):
            raise forms.ValidationError({
                'loan_interest_payment_date': 'Day of month must be between 1 and 31.'
            })
        
        return cleaned_data


class PushNotificationForm(forms.ModelForm):
    class Meta:
        model = PushNotification
        fields = ['title', 'body', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter notification title'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Enter notification body'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
        labels = {
            'title': 'Title',
            'body': 'Body',
            'image': 'Image (Optional)',
        }
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title or len(title.strip()) == 0:
            raise forms.ValidationError('Title is required.')
        if len(title) > 255:
            raise forms.ValidationError('Title must be 255 characters or less.')
        return title.strip()
    
    def clean_body(self):
        body = self.cleaned_data.get('body')
        if not body or len(body.strip()) == 0:
            raise forms.ValidationError('Body is required.')
        return body.strip()


class PopupForm(forms.ModelForm):
    class Meta:
        model = Popup
        fields = ['title', 'description', 'image', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter popup title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Enter popup description'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'title': 'Title',
            'description': 'Description',
            'image': 'Image (Optional)',
            'is_active': 'Is Active',
        }
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title or len(title.strip()) == 0:
            raise forms.ValidationError('Title is required.')
        if len(title) > 255:
            raise forms.ValidationError('Title must be 255 characters or less.')
        return title.strip()
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description or len(description.strip()) == 0:
            raise forms.ValidationError('Description is required.')
        return description.strip()