from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="restaurants"),
    path("photo/<int:pk>/", views.photo, name="restaurants_photo"),
    path("<slug:slug>/owner/", views.owner_update, name="restaurants_owner"),
]
