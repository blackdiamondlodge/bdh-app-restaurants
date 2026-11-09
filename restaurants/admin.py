from django.contrib import admin
from django.utils.html import format_html

from .models import Photo, Restaurant


class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 0
    fields = ("preview", "position", "author", "fetched_at")
    readonly_fields = fields
    can_delete = True

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Photo")
    def preview(self, obj):
        from django.urls import reverse
        return format_html('<img src="{}" style="height:60px;border-radius:6px">',
                           reverse("restaurants_photo", args=[obj.pk]))


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "pick", "hidden", "place_id", "fetched_at")
    list_filter = ("category", "pick", "hidden")
    search_fields = ("name", "slug", "place_id")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("fetched_at", "photos_fetched_at")
    inlines = [PhotoInline]
