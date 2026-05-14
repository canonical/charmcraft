from django.urls import path  # ty:ignore[unresolved-import]

from . import views  # ty:ignore[unresolved-import]

urlpatterns = [
    path("", views.index, name="index"),
]
