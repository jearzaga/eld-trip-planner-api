from django.db import connection
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from geo.provider import get_provider

MIN_GEOCODE_QUERY_LENGTH = 3


class HealthView(APIView):
    def get(self, request):
        try:
            # pymongo Database exposed by django-mongodb-backend
            connection.database.command("ping")
        except Exception:
            return Response({"status": "unavailable"}, status=503)
        return Response({"status": "ok"})


class GeocodeView(APIView):
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
