from django.http import Http404
from rest_framework.exceptions import APIException, NotFound, ParseError, ValidationError
from rest_framework.response import Response

from geo.provider import ProviderUnavailable, RouteNotFound

VALIDATION_ERROR = "VALIDATION_ERROR"
NOT_FOUND = "NOT_FOUND"
ROUTE_NOT_FOUND = "ROUTE_NOT_FOUND"
PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"


def _error_response(status_code, code, message, fields=None):
    payload = {"error": {"code": code, "message": message, "fields": fields or {}}}
    return Response(payload, status=status_code)


def _flatten_validation_fields(detail):
    fields: dict[str, list[str]] = {}

    def add(path, messages):
        key = path or "non_field_errors"
        fields.setdefault(key, []).extend(str(message) for message in messages)

    def walk(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}" if path else str(key))
        elif isinstance(node, list):
            leaves = [item for item in node if not isinstance(item, (dict, list))]
            if leaves:
                add(path, leaves)
            for index, item in enumerate(node):
                if isinstance(item, (dict, list)):
                    walk(item, f"{path}.{index}" if path else str(index))
        else:
            add(path, [node])

    walk(detail, "")
    return fields


def api_exception_handler(exc, context):
    if isinstance(exc, RouteNotFound):
        return _error_response(422, ROUTE_NOT_FOUND, "No truck route connects these locations.")
    if isinstance(exc, ProviderUnavailable):
        return _error_response(
            502,
            PROVIDER_UNAVAILABLE,
            "Routing or geocoding service is unavailable. Try again shortly.",
        )
    if isinstance(exc, Http404):
        exc = NotFound()
    if isinstance(exc, ParseError):
        return _error_response(400, VALIDATION_ERROR, "Invalid request.")
    if isinstance(exc, ValidationError):
        return _error_response(
            400, VALIDATION_ERROR, "Invalid request.", _flatten_validation_fields(exc.detail)
        )
    if isinstance(exc, NotFound):
        return _error_response(404, NOT_FOUND, str(exc.detail))
    if isinstance(exc, APIException):
        return _error_response(exc.status_code, exc.default_code.upper(), str(exc.detail))
    return None
