from django.utils import timezone

from bdh_sdk import INFO, ON, Status

from . import catalog
from .models import Restaurant
from .places import maybe_refresh_async


def status():
    maybe_refresh_async()
    restaurants = list(Restaurant.objects.filter(hidden=False).only("data"))
    if not any(r.data for r in restaurants):
        return None
    now = timezone.now()
    open_now = sum(1 for r in restaurants if catalog.status(r.data, now)[0] == "open")
    if open_now:
        return Status(f"{open_now} open now", ON)
    return Status("All closed right now", INFO)
