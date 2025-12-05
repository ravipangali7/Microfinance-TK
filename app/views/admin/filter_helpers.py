"""
Helper functions for filtering list views
"""
from datetime import date, datetime, timedelta
from calendar import monthrange
from django.db.models import Q
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
    """
    if start_date:
        queryset = queryset.filter(**{f"{date_field}__gte": start_date})
    if end_date:
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

