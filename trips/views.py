from django.db import connection
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    def get(self, request):
        try:
            # pymongo Database exposed by django-mongodb-backend
            connection.database.command("ping")
        except Exception:
            return Response({"status": "unavailable"}, status=503)
        return Response({"status": "ok"})
