from django.urls import path

from .views import GeocodeView, HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("geocode/", GeocodeView.as_view(), name="geocode"),
]
