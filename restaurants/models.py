from django.db import models

from .catalog import CATEGORY_CHOICES


class Restaurant(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="family")
    tags = models.CharField(
        max_length=200, blank=True,
        help_text="Extra filter tags, space separated: coffee breakfast lunch apres dinner. "
                  "Google adds the rest.",
    )
    place_id = models.CharField(
        "Google place ID", max_length=200, blank=True,
        help_text="Leave blank for places Google doesn't list.",
    )
    pick = models.BooleanField("Owner's pick", default=False)
    note = models.TextField("Owner's note", blank=True, help_text="Shown to guests in the details view.")
    hidden = models.BooleanField(default=False, help_text="Hide from guests.")
    data = models.JSONField(default=dict, blank=True, help_text="Place details from Google.")
    fetched_at = models.DateTimeField(null=True, blank=True)
    photos_fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Photo(models.Model):
    """A Google photo, stored in the database so it is only downloaded
    (and billed) about once a month rather than on every page view."""

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="photos")
    position = models.PositiveSmallIntegerField(default=0)
    image = models.BinaryField()
    content_type = models.CharField(max_length=50, default="image/jpeg")
    author = models.CharField(max_length=200, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["restaurant", "position"]

    def __str__(self):
        return f"{self.restaurant} #{self.position}"
