# bdh-app-restaurants

BlackDiamondHub plugin app: **Restaurants** — every place to eat in Sun Peaks
with Google ratings, open-now status, photos, a clustered map, a guest
shortlist (with "send to my phone" QR) and owner picks/notes.

## Configuration

| Setting | Env var | Default |
|---|---|---|
| Google Places API key | `BDH_RESTAURANTS_GOOGLE_PLACES_API_KEY` or `GOOGLE_PLACES_API_KEY` | empty (no fetching) |
| Shortlist page | `BDH_RESTAURANTS_SHORTLIST_URL` | `https://blackdiamondlodge.github.io/shortlist/` |

The key needs **Places API (New)** enabled and billing on (photos are a paid SKU).

## Data refresh & cost

- Place details refresh at most every ~20 h, photos (3 per place) every 30 days.
- Photos are cached in the database and served with immutable cache headers —
  Google is never hit per page view.
- Refresh runs lazily in a background thread when the homepage or the app is
  viewed (1 h lock). Force a refresh with:

  ```
  python manage.py refresh_restaurants --force
  ```

## Owner editing

Signed-in users see an owner panel in each restaurant's details:
**Owner's pick**, an **owner's note** (shown to guests, independent of the pick)
and **Hide from guests**. Places are added/removed in Django admin (they need a
Google `place_id` for data).

## Shortlist

Guests heart places (stored in the kiosk browser for the whole stay). The list
resets when a different stay begins, using the hub's `hub_stay_key` template
variable; checkout or an HA outage never clears it, and a list started before a
stay shows up is kept for that stay. "Send
list to my phone" shows a QR to the static shortlist page, with the list encoded
in the URL hash — nothing is stored server-side and it works off the lodge LAN.

On phones (≤600px) the page switches to a single-column list: quick filter
chips sit under the title, the full filter groups open in a bottom sheet, and a
floating "♥ Shortlist" button opens the shortlist as a bottom sheet with
directions links and a Share button (`navigator.share` with the same shortlist
link, falling back to the QR).

To keep that QR sparse, each place goes in the link as a 3-character code that
the page looks up in its `places.json`. The kiosk only uses a code when the
published file lists the same name and place ID; otherwise that place goes in
the long `Name~PlaceID` form, so links always work. After adding or renaming
restaurants, refresh the file in the
[shortlist repo](https://github.com/blackdiamondlodge/shortlist):

    python manage.py export_shortlist_places --merge places.json > new.json
