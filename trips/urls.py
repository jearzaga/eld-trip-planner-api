from django.urls import path

from .views import GeocodeView, HealthView, TripCreateView, TripDetailView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("geocode/", GeocodeView.as_view(), name="geocode"),
    path("trips/", TripCreateView.as_view(), name="trip-create"),
    path("trips/<str:trip_id>/", TripDetailView.as_view(), name="trip-detail"),
]
