"""
Helper functions for filtering list views
"""
from datetime import date, datetime, timedelta, time
from calendar import monthrange
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal


def get_default_date_range():
    """
    Get default date range (last 1 month from today)
    Returns tuple (start_date, end_date)
    """
    end_date = date.today()
    # Calculate start date (1 month ago)
    if end_date.month == 1:
        start_date = date(end_date.year - 1, 12, end_date.day)
    else:
        # Get the last day of previous month
        last_day_prev_month = monthrange(end_date.year, end_date.month - 1)[1]
        start_date = date(end_date.year, end_date.month - 1, min(end_date.day, last_day_prev_month))
    return start_date, end_date


def parse_date_range(date_range_string):
    """
    Parse date range string in format "YYYY-MM-DD to YYYY-MM-DD"
    Returns tuple (start_date, end_date) or None if invalid
    """
    if not date_range_string:
        return None
    
    try:
        parts = date_range_string.split(' to ')
        if len(parts) == 2:
            start_date = datetime.strptime(parts[0].strip(), '%Y-%m-%d').date()
            end_date = datetime.strptime(parts[1].strip(), '%Y-%m-%d').date()
            return start_date, end_date
        elif len(parts) == 1:
            # Single date, use as both start and end
            single_date = datetime.strptime(parts[0].strip(), '%Y-%m-%d').date()
            return single_date, single_date
    except (ValueError, AttributeError):
        return None
    
    return None


def format_date_range(start_date, end_date):
    """
    Format date range tuple to string format "YYYY-MM-DD to YYYY-MM-DD"
    """
    if start_date and end_date:
        return f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    return ""


def apply_text_search(queryset, search_term, search_fields):
    """
    Apply text search across multiple fields using Q objects
    """
    if not search_term:
        return queryset
    
    search_term = search_term.strip()
    if not search_term:
        return queryset
    
    q_objects = Q()
    for field in search_fields:
        q_objects |= Q(**{f"{field}__icontains": search_term})
    
    return queryset.filter(q_objects)


def apply_date_filter(queryset, date_field, start_date=None, end_date=None):
    """
    Apply date range filter to queryset
    
    For datetime fields:
    - Start date: 00:00:00 (beginning of day)
    - End date: 23:59:59.999999 (end of day)
    
    For date fields:
    - Uses date comparison directly (no time component)
    
    Args:
        queryset: Django queryset to filter
        date_field: Name of the field to filter on
        start_date: Start date (date object)
        end_date: End date (date object)
    
    Returns:
        Filtered queryset
    """
    if not start_date and not end_date:
        return queryset
    
    # Get the model from queryset to check field type
    model = queryset.model
    field = None
    
    # Handle related field lookups (e.g., 'user__created_at')
    field_parts = date_field.split('__')
    if len(field_parts) > 1:
        # For related fields, we'll assume datetime and convert
        # This is a simplified approach - could be enhanced to traverse relationships
        field_name = field_parts[-1]
    else:
        field_name = date_field
    
    # Try to get the field from the model
    try:
        field = model._meta.get_field(field_name)
    except:
        # If field not found (might be a related field or custom lookup), 
        # assume it's a datetime field and convert dates to datetimes
        pass
    
    # Determine if field is a DateTimeField
    is_datetime_field = False
    if field:
        from django.db.models import DateTimeField
        is_datetime_field = isinstance(field, DateTimeField)
    else:
        # If we can't determine, check if field name suggests datetime
        # Common datetime field names: created_at, updated_at, timestamp, etc.
        datetime_indicators = ['created_at', 'updated_at', 'timestamp', 'datetime', 'time']
        is_datetime_field = any(indicator in field_name.lower() for indicator in datetime_indicators)
    
    # Apply filters with proper time handling
    if start_date:
        if is_datetime_field:
            # Convert date to datetime at start of day (00:00:00)
            start_datetime = datetime.combine(start_date, time.min)
            # Make timezone-aware if USE_TZ is enabled in Django settings
            from django.conf import settings
            if getattr(settings, 'USE_TZ', False):
                # Django uses timezone-aware datetimes
                start_datetime = timezone.make_aware(start_datetime)
            queryset = queryset.filter(**{f"{date_field}__gte": start_datetime})
        else:
            # Date field - use date directly
            queryset = queryset.filter(**{f"{date_field}__gte": start_date})
    
    if end_date:
        if is_datetime_field:
            # Convert date to datetime at end of day (23:59:59.999999)
            end_datetime = datetime.combine(end_date, time.max)
            # Make timezone-aware if USE_TZ is enabled in Django settings
            from django.conf import settings
            if getattr(settings, 'USE_TZ', False):
                # Django uses timezone-aware datetimes
                end_datetime = timezone.make_aware(end_datetime)
            queryset = queryset.filter(**{f"{date_field}__lte": end_datetime})
        else:
            # Date field - use date directly
            queryset = queryset.filter(**{f"{date_field}__lte": end_date})
    
    return queryset


def apply_amount_range_filter(queryset, amount_field, from_amount=None, to_amount=None):
    """
    Apply amount range filter to queryset
    """
    if from_amount:
        try:
            from_amount = Decimal(str(from_amount))
            queryset = queryset.filter(**{f"{amount_field}__gte": from_amount})
        except (ValueError, TypeError):
            pass
    if to_amount:
        try:
            to_amount = Decimal(str(to_amount))
            queryset = queryset.filter(**{f"{amount_field}__lte": to_amount})
        except (ValueError, TypeError):
            pass
    return queryset

