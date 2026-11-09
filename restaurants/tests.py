import datetime as dt
import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings, tag
from django.urls import reverse
from django.utils import timezone

from restaurants import catalog, places
from restaurants.homepage import status as homepage_status
from restaurants.models import Photo, Restaurant

UTC = dt.timezone.utc


def weekly(open_h, close_h, days=range(7), close_next_day=False):
    return {"periods": [{"open": {"day": d, "hour": open_h, "minute": 0},
                         "close": {"day": (d + 1) % 7 if close_next_day else d, "hour": close_h, "minute": 0}}
                        for d in days],
            "weekdayDescriptions": ["Monday: 8:00\u202fAM\u2009\u2013\u20095:00\u202fPM"]}


def place(**extra):
    data = {"id": "pid", "rating": 4.5, "userRatingCount": 120, "utcOffsetMinutes": -420,
            "location": {"latitude": 50.8835, "longitude": -119.8865},
            "regularOpeningHours": weekly(8, 17), "googleMapsUri": "https://maps.google.com/?cid=1"}
    data.update(extra)
    return data


def local(y, mo, d, h, mi=0):
    """A UTC instant for the given wall-clock time in Sun Peaks (UTC-7)."""
    return dt.datetime(y, mo, d, h, mi, tzinfo=dt.timezone(dt.timedelta(hours=-7))).astimezone(UTC)


# 2026-11-09 is a Monday.
class StatusTests(TestCase):
    def test_open_and_closing_time(self):
        self.assertEqual(catalog.status(place(), local(2026, 11, 9, 9, 55)), ("open", "Open · until 5pm"))

    def test_uses_place_offset_not_server_timezone(self):
        # 5:30pm in Sun Peaks; a server that thinks BC is on PST would say 4:30pm, still open.
        self.assertEqual(catalog.status(place(), local(2026, 11, 9, 17, 30))[0], "closed")

    def test_opens_later_today_tomorrow_and_weekday(self):
        self.assertEqual(catalog.status(place(), local(2026, 11, 9, 6)), ("closed", "Opens 8am"))
        self.assertEqual(catalog.status(place(), local(2026, 11, 9, 18)), ("closed", "Opens tomorrow 8am"))
        friday_only = place(regularOpeningHours=weekly(11, 21, days=[5]))
        self.assertEqual(catalog.status(friday_only, local(2026, 11, 9, 12)), ("closed", "Opens Fri 11am"))

    def test_overnight_hours(self):
        late = place(regularOpeningHours=weekly(17, 2, close_next_day=True))
        self.assertEqual(catalog.status(late, local(2026, 11, 10, 1)), ("open", "Open · until 2am"))
        # Saturday night into Sunday wraps the week.
        sat = place(regularOpeningHours=weekly(20, 0, days=[6], close_next_day=True))
        self.assertEqual(catalog.status(sat, local(2026, 11, 14, 23, 30)), ("open", "Open · until midnight"))
        self.assertEqual(catalog.status(sat, local(2026, 11, 15, 0, 30))[0], "closed")

    def test_half_hours(self):
        data = place(regularOpeningHours={"periods": [
            {"open": {"day": 1, "hour": 8, "minute": 30}, "close": {"day": 1, "hour": 14, "minute": 30}}]})
        self.assertEqual(catalog.status(data, local(2026, 11, 9, 8)), ("closed", "Opens 8:30am"))
        self.assertEqual(catalog.status(data, local(2026, 11, 9, 9)), ("open", "Open · until 2:30pm"))

    def test_always_open_seasonal_and_unknown(self):
        always = place(regularOpeningHours={"periods": [{"open": {"day": 0, "hour": 0, "minute": 0}}]})
        self.assertEqual(catalog.status(always, local(2026, 11, 9, 3)), ("open", "Open 24 hours"))
        self.assertEqual(catalog.status(place(businessStatus="CLOSED_TEMPORARILY"))[0], "season")
        self.assertEqual(catalog.status(place(businessStatus="FUTURE_OPENING")), ("season", "Opening soon"))
        self.assertEqual(catalog.status({}), ("unknown", "Hours unavailable"))
        self.assertEqual(catalog.status(place(regularOpeningHours={}))[0], "unknown")


class CatalogTests(TestCase):
    def test_tags_combine_curation_google_and_pick(self):
        r = Restaurant(slug="x", name="X", category="cafe", tags="apres", pick=True,
                       data={"servesBrunch": True, "menuForChildren": True, "outdoorSeating": True, "reservable": False})
        self.assertEqual(catalog.tags(r), {"apres", "coffee", "breakfast", "kids", "patio", "pick"})

    def test_item(self):
        r = Restaurant(slug="x", name="X", category="pizza", place_id="pid", note="Call ahead",
                       data=place(priceLevel="PRICE_LEVEL_MODERATE", takeout=True,
                                  editorialSummary={"text": "Wood-fired pizza."}))
        i = catalog.item(r, [], local(2026, 11, 9, 12))
        self.assertEqual(i["price"], "$$")
        self.assertEqual(i["st"], ["open", "Open · until 5pm"])
        self.assertIn("open", i["tags"].split())
        self.assertEqual(i["summary"], "Wood-fired pizza.")
        self.assertEqual(i["amen"], [["fa-bag-shopping", "Takeout"]])
        self.assertTrue(i["dist"].startswith("1.6 km"))
        self.assertEqual(i["note"], "Call ahead")

    def test_place_without_google_data(self):
        r = Restaurant(slug="fondue", name="Fondue Stube", category="fondue")
        i = catalog.item(r, [])
        self.assertEqual(i["st"][0], "unknown")
        self.assertIsNone(i["loc"])
        self.assertIn("google.com/maps/search", i["maps"])


class SeedTests(TestCase):
    def test_seeded(self):
        self.assertEqual(Restaurant.objects.count(), 23)
        self.assertEqual(Restaurant.objects.exclude(place_id="").count(), 22)
        self.assertFalse(Restaurant.objects.filter(pick=True).exists())


def response(json_data=None, content=b"", content_type="application/json"):
    r = MagicMock()
    r.json.return_value = json_data
    r.content = content
    r.headers = {"Content-Type": content_type}
    r.raise_for_status.return_value = None
    return r


@override_settings(BDH_RESTAURANTS_GOOGLE_PLACES_API_KEY="k")
class RefreshTests(TestCase):
    def setUp(self):
        Restaurant.objects.exclude(slug__in=["bolacco-cafe", "fondue-stube"]).delete()
        self.r = Restaurant.objects.get(slug="bolacco-cafe")

    def fake_get(self, url, **kwargs):
        if url.endswith("/media"):
            return response(content=b"jpeg", content_type="image/jpeg")
        return response(place(photos=[{"name": f"places/pid/photos/{n}",
                                       "authorAttributions": [{"displayName": f"A{n}"}]} for n in range(5)]))

    def test_fetches_details_and_three_photos(self):
        with patch("restaurants.places.requests.get", side_effect=self.fake_get) as get:
            counts = places.refresh()
        self.assertEqual(counts, {"details": 1, "photos": 3, "errors": 0, "skipped": False})
        self.assertEqual(get.call_count, 4)
        self.assertEqual(get.call_args_list[0].kwargs["headers"]["X-Goog-Api-Key"], "k")
        self.r.refresh_from_db()
        self.assertEqual(self.r.data["rating"], 4.5)
        self.assertEqual([p.author for p in self.r.photos.all()], ["A0", "A1", "A2"])
        self.assertEqual(bytes(self.r.photos.first().image), b"jpeg")

    def test_photos_not_refetched_with_daily_details(self):
        with patch("restaurants.places.requests.get", side_effect=self.fake_get):
            places.refresh()
        tomorrow = timezone.now() + dt.timedelta(days=1)
        with patch("restaurants.places.requests.get", side_effect=self.fake_get) as get:
            counts = places.refresh(now=tomorrow)
        self.assertEqual((counts["details"], counts["photos"]), (1, 0))
        self.assertEqual(get.call_count, 1)
        with patch("restaurants.places.requests.get", side_effect=self.fake_get) as get:
            places.refresh(now=tomorrow + dt.timedelta(hours=1))
        get.assert_not_called()
        with patch("restaurants.places.requests.get", side_effect=self.fake_get) as get:
            counts = places.refresh(now=timezone.now() + dt.timedelta(days=31))
        self.assertEqual(counts["photos"], 3)
        self.assertEqual(Photo.objects.count(), 3)

    def test_overlapping_refreshes_fetch_and_save_once(self):
        # A second refresh (page thread vs management command) starts while
        # the first is downloading photos: it must not call Google again.
        nested = []

        def get(url, **kwargs):
            if url.endswith("/media") and not nested:
                nested.append(places.refresh())
            return self.fake_get(url, **kwargs)

        with patch("restaurants.places.requests.get", side_effect=get) as mock:
            counts = places.refresh()
        self.assertEqual(nested[0], {"details": 0, "photos": 0, "errors": 0, "skipped": False})
        self.assertEqual((counts["details"], counts["photos"]), (1, 3))
        self.assertEqual(mock.call_count, 4)
        self.assertEqual(self.r.photos.count(), 3)

    def test_failure_keeps_old_data_and_waits_a_day(self):
        self.r.data = {"rating": 4.0}
        self.r.save()
        with patch("restaurants.places.requests.get", side_effect=places.requests.ConnectionError("down")):
            counts = places.refresh()
        self.assertEqual(counts["errors"], 1)
        self.r.refresh_from_db()
        self.assertEqual(self.r.data, {"rating": 4.0})
        self.assertFalse(places.needs_refresh())

    @override_settings(BDH_RESTAURANTS_GOOGLE_PLACES_API_KEY="")
    def test_no_key_no_calls(self):
        with patch("restaurants.places.requests.get") as get, patch("restaurants.places.threading.Thread") as thread:
            self.assertTrue(places.refresh()["skipped"])
            self.assertFalse(places.maybe_refresh_async())
        get.assert_not_called()
        thread.assert_not_called()

    def test_async_refresh_is_rate_limited(self):
        cache.delete(places.LOCK)
        with patch("restaurants.places.threading.Thread") as thread:
            self.assertTrue(places.maybe_refresh_async())
            self.assertFalse(places.maybe_refresh_async())
        thread.assert_called_once()
        cache.delete(places.LOCK)

    def test_management_command(self):
        with patch("restaurants.places.requests.get", side_effect=self.fake_get):
            call_command("refresh_restaurants", stdout=MagicMock())
        self.assertEqual(Photo.objects.count(), 3)


@override_settings(BDH_RESTAURANTS_GOOGLE_PLACES_API_KEY="")
class ViewTests(TestCase):
    def setUp(self):
        self.url = reverse("restaurants")
        self.r = Restaurant.objects.get(slug="bolacco-cafe")
        self.r.data = place()
        self.r.save()
        self.photo = Photo.objects.create(restaurant=self.r, image=b"img", author="Jun")
        Restaurant.objects.filter(slug="powder-hounds").update(hidden=True, note="secret")
        self.user = get_user_model().objects.create_user("owner", password="pw")

    def test_guest_page(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Bolacco Café")
        self.assertContains(r, reverse("restaurants_photo", args=[self.photo.pk]))
        self.assertNotContains(r, "Powder Hounds")
        self.assertFalse(r.context["config"]["owner"])

    def test_owner_sees_hidden(self):
        self.client.force_login(self.user)
        r = self.client.get(self.url)
        self.assertContains(r, "Powder Hounds")
        self.assertTrue(r.context["config"]["owner"])

    def test_photo(self):
        r = self.client.get(reverse("restaurants_photo", args=[self.photo.pk]))
        self.assertEqual(r.content, b"img")
        self.assertEqual(r["Content-Type"], "image/jpeg")
        self.assertIn("immutable", r["Cache-Control"])

    def test_hidden_photo_is_owner_only(self):
        hidden = Photo.objects.create(restaurant=Restaurant.objects.get(slug="powder-hounds"), image=b"x")
        url = reverse("restaurants_photo", args=[hidden.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_owner_update(self):
        url = reverse("restaurants_owner", args=["bolacco-cafe"])
        body = json.dumps({"pick": True, "note": "  Best coffee  ", "hidden": False})
        self.assertEqual(self.client.post(url, body, content_type="application/json").status_code, 403)
        self.client.force_login(self.user)
        r = self.client.post(url, body, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["pick"])
        self.assertIn("pick", r.json()["tags"].split())
        self.r.refresh_from_db()
        self.assertEqual((self.r.pick, self.r.note), (True, "Best coffee"))
        # The note stands on its own when the pick is removed.
        self.client.post(url, json.dumps({"pick": False}), content_type="application/json")
        self.r.refresh_from_db()
        self.assertEqual((self.r.pick, self.r.note), (False, "Best coffee"))

    def test_homepage_status(self):
        open_now = local(2026, 11, 9, 12)
        with patch("restaurants.homepage.timezone.now", return_value=open_now):
            s = homepage_status()
        self.assertEqual((s.text, s.level), ("1 open now", "on"))
        Restaurant.objects.update(data={})
        self.assertIsNone(homepage_status())


@tag("selenium")
@override_settings(BDH_RESTAURANTS_GOOGLE_PLACES_API_KEY="")
class BrowserTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from selenium import webdriver
        options = webdriver.ChromeOptions()
        for arg in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--window-size=1920,1080"):
            options.add_argument(arg)
        cls.driver = webdriver.Chrome(options=options)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def test_details_shortlist_and_filters(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        Restaurant.objects.filter(slug="bolacco-cafe").update(data=place(), pick=True, note="Get the sandwich")
        d = self.driver
        d.get(self.live_server_url + reverse("restaurants"))
        wait = WebDriverWait(d, 10)
        d.find_element(By.CSS_SELECTOR, '.rc[data-slug="bolacco-cafe"] .hb').click()
        wait.until(EC.text_to_be_present_in_element((By.ID, "rs-list"), "Bolacco Café"))
        d.find_element(By.CSS_SELECTOR, '.rc[data-slug="bolacco-cafe"] .nm').click()
        wait.until(EC.visibility_of_element_located((By.ID, "rs-dlg")))
        self.assertIn("Get the sandwich", d.find_element(By.CSS_SELECTOR, "#rs-dlg .note").text)
        d.find_element(By.CSS_SELECTOR, "#rs-dlg .dclose").click()
        d.find_element(By.CSS_SELECTOR, '.chip[data-f="pick"]').click()
        shown = [e.get_attribute("data-slug") for e in d.find_elements(By.CSS_SELECTOR, ".rc:not(.hide)")]
        self.assertEqual(shown, ["bolacco-cafe"])
