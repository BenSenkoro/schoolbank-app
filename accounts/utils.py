from django.core.paginator import Paginator
from .models import ActivityLog


def paginate(request, queryset, per_page=25):
    """Return the requested page of a queryset. Bad or out-of-range ?page= values fall back to a valid page."""
    return Paginator(queryset, per_page).get_page(request.GET.get('page'))


def log_activity(user, action, description, request=None):
    """Call this anywhere in the system to log an activity."""
    ip = None
    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')

    ActivityLog.objects.create(
        user=user,
        action=action,
        description=description,
        ip_address=ip
    )