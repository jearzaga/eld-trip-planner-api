from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from geo.provider import get_provider
from trips.models import Trip
from trips.serializers import (
    ErrorResponseSerializer,
    GeocodeResultSerializer,
    HealthResponseSerializer,
    TripRequestSerializer,
    TripResponseSerializer,
)
from trips.services import plan_trip

MIN_GEOCODE_QUERY_LENGTH = 3


class HealthView(APIView):
    @extend_schema(
        operation_id="health_check",
        responses={200: HealthResponseSerializer, 503: HealthResponseSerializer},
    )
    def get(self, request):
        try:
            # pymongo Database exposed by django-mongodb-backend
            connection.database.command("ping")
        except Exception:
            return Response({"status": "unavailable"}, status=503)
        return Response({"status": "ok"})


class GeocodeView(APIView):
    @extend_schema(
        operation_id="geocode_search",
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Search text, at least 3 characters.",
            )
        ],
        responses={
            200: GeocodeResultSerializer(many=True),
            400: ErrorResponseSerializer,
            502: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < MIN_GEOCODE_QUERY_LENGTH:
            raise ValidationError(
                {"q": [f"Search query must be at least {MIN_GEOCODE_QUERY_LENGTH} characters."]}
            )
        places = get_provider().geocode(query)
        return Response(
            [{"label": place.label, "lat": place.lat, "lng": place.lng} for place in places]
        )


class TripCreateView(APIView):
    @extend_schema(
        operation_id="trips_create",
        request=TripRequestSerializer,
        responses={
            201: TripResponseSerializer,
            400: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
            502: ErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = TripRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = plan_trip(serializer.validated_data)
        trip = Trip.from_plan(plan)
        trip.save()
        return Response(trip.to_response(), status=201)


class TripDetailView(APIView):
    @extend_schema(
        operation_id="trips_retrieve",
        responses={200: TripResponseSerializer, 404: ErrorResponseSerializer},
    )
    def get(self, request, trip_id):
        try:
            trip = Trip.objects.get(pk=trip_id)
        except (Trip.DoesNotExist, DjangoValidationError):
            raise NotFound() from None
        return Response(trip.to_response())
