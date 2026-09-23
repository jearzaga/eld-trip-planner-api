import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_list(name: str, default: str = "") -> list[str]:
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


def env_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} is not set. Add it to .env (see .env.example).")
    return value


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

# No admin/auth/sessions: the app has no login (out of scope)
INSTALLED_APPS = [
    "django_mongodb_backend",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "trips",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must come before CommonMiddleware
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# --- MongoDB Atlas (django-mongodb-backend >= 5.2.1 accepts a connection string in HOST) ---
# There is no local MongoDB: every environment (dev, tests, E2E, CI, Render) uses an Atlas SRV URI.
DATABASES = {
    "default": {
        "ENGINE": "django_mongodb_backend",
        "HOST": env_required("MONGODB_URI"),
        "NAME": os.environ.get("MONGODB_DB", "eld"),
    }
}
DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"
DATABASE_ROUTERS = ["django_mongodb_backend.routers.MongoRouter"]  # required for embedded models

# --- DRF: JSON only, no auth ---
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "trips.exceptions.api_exception_handler",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "ELD Trip Planner API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "DutyStatusEnum": ["OFF", "SB", "D", "ON"],
        "StopTypeEnum": ["pickup", "fuel", "break_30", "rest_10", "restart_34", "dropoff"],
        "HealthStatusEnum": ["ok", "unavailable"],
    },
}

# --- CORS (Vercel prod + previews) ---
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
CORS_ALLOWED_ORIGIN_REGEXES = env_list("CORS_ALLOWED_ORIGIN_REGEXES")

# --- Time: store UTC; convert to home-terminal time only in the log builder ---
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"

# --- App settings ---
GEO_PROVIDER = os.environ.get("GEO_PROVIDER", "fake")  # fake | live
ORS_API_KEY = os.environ.get("ORS_API_KEY", "")
PHOTON_URL = os.environ.get("PHOTON_URL", "https://photon.komoot.io")

# --- Production hardening (Render terminates TLS in front of the app) ---
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
