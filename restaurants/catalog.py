"""Turns stored restaurants (our curation + Google's place data) into what
the page shows: tags for the filters, open/closed status, distance, etc.

Opening status is computed from the weekly hours and the place's own UTC
offset rather than Google's ``openNow``, which goes stale between daily
refreshes, and rather than the server's tz database, which may not know that
BC stays on UTC-7 all year.
"""
import datetime as dt
import math
from collections import namedtuple

LODGE = (50.8847045, -119.8641833)
# Sun Peaks is on UTC-7 all year; used when Google didn't send an offset.
DEFAULT_UTC_OFFSET_MINUTES = -7 * 60

Category = namedtuple("Category", "icon label c1 c2")
CATEGORIES = {
    "cafe": Category("fa-mug-hot", "Café", "#c08552", "#5b3a29"),
    "pub": Category("fa-beer-mug-empty", "Pub & grill", "#e0a030", "#5a3d10"),
    "family": Category("fa-utensils", "Casual", "#4fa3a5", "#1c4a4b"),
    "treats": Category("fa-ice-cream", "Treats", "#e57aa8", "#5a2440"),
    "italian": Category("fa-wine-bottle", "Italian", "#d0574b", "#4f1d18"),
    "burger": Category("fa-burger", "Diner", "#e8833a", "#5a2e10"),
    "fondue": Category("fa-cheese", "Fondue", "#e3c04a", "#5a4810"),
    "fine": Category("fa-wine-glass", "Fine dining", "#9b7be0", "#33245a"),
    "pizza": Category("fa-pizza-slice", "Pizza", "#e8663a", "#5a2510"),
    "japanese": Category("fa-fish", "Japanese", "#e05a6a", "#4f1a22"),
    "german": Category("fa-drumstick-bite", "German", "#b8a060", "#4a3d1a"),
}
CATEGORY_CHOICES = [(key, cat.label) for key, cat in CATEGORIES.items()]

PRICE = {
    "PRICE_LEVEL_INEXPENSIVE": "$",
    "PRICE_LEVEL_MODERATE": "$$",
    "PRICE_LEVEL_EXPENSIVE": "$$$",
    "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
}

# Google attribute -> (icon, label) shown as chips in the details view.
AMENITIES = [
    ("takeout", "fa-bag-shopping", "Takeout"),
    ("delivery", "fa-truck", "Delivery"),
    ("reservable", "fa-calendar-check", "Reservations"),
    ("menuForChildren", "fa-child", "Kids menu"),
    ("outdoorSeating", "fa-umbrella-beach", "Patio"),
    ("allowsDogs", "fa-dog", "Dogs OK"),
    ("liveMusic", "fa-music", "Live music"),
    ("goodForWatchingSports", "fa-tv", "Sports on TV"),
]

# Filter groups: (id, label, how chips combine, [(tag, label, icon)]).
FILTER_GROUPS = [
    ("show", "Show", "and", [
        ("open", "Open now", "fa-door-open"),
        ("pick", "Owner's picks", "fa-star"),
    ]),
    ("meal", "Meal", "or", [
        ("coffee", "Coffee", "fa-mug-hot"),
        ("breakfast", "Breakfast", "fa-egg"),
        ("lunch", "Lunch", "fa-burger"),
        ("apres", "Après", "fa-beer-mug-empty"),
        ("dinner", "Dinner", "fa-utensils"),
    ]),
    ("good", "Good for", "and", [
        ("kids", "Kids", "fa-child"),
        ("groups", "Groups", "fa-user-group"),
        ("reserve", "Reservations", "fa-calendar-check"),
        ("patio", "Patio", "fa-umbrella-beach"),
    ]),
]

STATUS_ORDER = {"open": 0, "closed": 1, "unknown": 2, "season": 3}
DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
WEEK = 7 * 24 * 60


def local_now(data, now=None):
    """``now`` in the restaurant's local time."""
    now = now or dt.datetime.now(dt.timezone.utc)
    offset = data.get("utcOffsetMinutes", DEFAULT_UTC_OFFSET_MINUTES) if data else DEFAULT_UTC_OFFSET_MINUTES
    return now.astimezone(dt.timezone(dt.timedelta(minutes=offset)))


def _minute_of_week(point):
    return point.get("day", 0) * 1440 + point.get("hour", 0) * 60 + point.get("minute", 0)


def clock(hour, minute=0):
    """9 -> '9am', 17:30 -> '5:30pm', 0 -> 'midnight'."""
    if hour % 24 == 0 and minute == 0:
        return "midnight"
    h12 = hour % 12 or 12
    text = f"{h12}:{minute:02d}" if minute else str(h12)
    return text + ("am" if hour % 24 < 12 else "pm")


def status(data, now=None):
    """Return ``(state, text)``; state is open, closed, unknown or season."""
    if not data:
        return ("unknown", "Hours unavailable")
    business = data.get("businessStatus")
    # Sun Peaks venues mark the off-season as either of these.
    if business in ("CLOSED_TEMPORARILY", "FUTURE_OPENING"):
        return ("season", "Closed for the season")
    if business == "CLOSED_PERMANENTLY":
        return ("season", "Permanently closed")
    periods = [p for p in (data.get("regularOpeningHours") or {}).get("periods") or [] if p.get("open")]
    if not periods:
        return ("unknown", "Hours unavailable")

    t = local_now(data, now)
    current = _minute_of_week({"day": (t.weekday() + 1) % 7, "hour": t.hour, "minute": t.minute})
    for p in periods:
        if not p.get("close"):
            return ("open", "Open 24 hours")
        start, end = _minute_of_week(p["open"]), _minute_of_week(p["close"])
        if end <= start:
            end += WEEK  # overnight across Saturday -> Sunday
        if start <= current < end or start <= current + WEEK < end:
            return ("open", "Open · until " + clock(p["close"].get("hour", 0), p["close"].get("minute", 0)))

    wait, nxt = min(((_minute_of_week(p["open"]) - current) % WEEK, p["open"]) for p in periods)
    opens = (t + dt.timedelta(minutes=wait)).date()
    if opens == t.date():
        day = ""
    elif opens == t.date() + dt.timedelta(days=1):
        day = "tomorrow "
    else:
        day = opens.strftime("%a ")
    return ("closed", f"Opens {day}{clock(nxt.get('hour', 0), nxt.get('minute', 0))}")


def distance_km(data):
    loc = (data or {}).get("location")
    if not loc:
        return None
    lat, lng = loc["latitude"], loc["longitude"]
    x = math.radians(lng - LODGE[1]) * math.cos(math.radians((LODGE[0] + lat) / 2))
    y = math.radians(lat - LODGE[0])
    return 6371 * math.hypot(x, y)


def tags(restaurant):
    """Filter tags: the curated ones plus what Google knows about the place."""
    data = restaurant.data or {}
    result = set(restaurant.tags.split())
    if restaurant.category == "cafe" or data.get("servesCoffee"):
        result.add("coffee")
    if data.get("servesBreakfast") or data.get("servesBrunch"):
        result.add("breakfast")
    if data.get("servesLunch"):
        result.add("lunch")
    if data.get("servesDinner"):
        result.add("dinner")
    if data.get("goodForChildren") or data.get("menuForChildren"):
        result.add("kids")
    for attr, tag in (("goodForGroups", "groups"), ("reservable", "reserve"), ("outdoorSeating", "patio")):
        if data.get(attr):
            result.add(tag)
    if restaurant.pick:
        result.add("pick")
    return result


def summary(data):
    for key, field in (("editorialSummary", "text"), ("generativeSummary", "overview")):
        value = (data or {}).get(key) or {}
        value = value.get(field)
        if isinstance(value, dict):
            value = value.get("text")
        if value:
            return value
    return ""


def maps_url(restaurant):
    data = restaurant.data or {}
    if data.get("googleMapsUri"):
        return data["googleMapsUri"]
    from urllib.parse import quote_plus
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(f"{restaurant.name} Sun Peaks")


def item(restaurant, photos, now=None):
    """Everything the page needs about one restaurant, JSON-serialisable."""
    data = restaurant.data or {}
    cat = CATEGORIES.get(restaurant.category, CATEGORIES["family"])
    state = status(data, now)
    tag_set = tags(restaurant)
    if state[0] == "open":
        tag_set.add("open")
    km = distance_km(data)
    loc = data.get("location")
    return {
        "slug": restaurant.slug,
        "name": restaurant.name,
        "icon": cat.icon,
        "label": cat.label,
        "c1": cat.c1,
        "c2": cat.c2,
        "tags": " ".join(sorted(tag_set)),
        "rating": data.get("rating"),
        "count": data.get("userRatingCount"),
        "price": PRICE.get(data.get("priceLevel"), ""),
        "st": list(state),
        "dist": f"{km:.1f} km · {max(2, round(km * 2.2))} min drive" if km else "",
        "summary": summary(data),
        "hours": [h.replace("\u202f", " ").replace("\u2009", "")
                  for h in (data.get("regularOpeningHours") or {}).get("weekdayDescriptions", [])],
        "phone": data.get("nationalPhoneNumber", ""),
        "pid": restaurant.place_id,
        "loc": [loc["latitude"], loc["longitude"]] if loc else None,
        "amen": [[icon, label] for attr, icon, label in AMENITIES if data.get(attr)],
        "photos": photos,
        "maps": maps_url(restaurant),
        "pick": restaurant.pick,
        "note": restaurant.note,
        "hidden": restaurant.hidden,
    }


def sort_key(entry):
    return (STATUS_ORDER.get(entry["st"][0], 9), -(entry["rating"] or 0), entry["name"])
