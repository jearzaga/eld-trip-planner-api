import os
import subprocess
import sys

from django.conf import settings

PRINT_SETTINGS = (
    "import django; django.setup(); from django.conf import settings as s; "
    "print(s.DATABASES['default']['NAME'], s.GEO_PROVIDER)"
)


def test_process_env_overrides_dotenv_for_e2e_and_tests():
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings",
        "MONGODB_URI": "mongodb+srv://u:p@cluster0.example.mongodb.net/",
        "MONGODB_DB": "eld_e2e",
        "GEO_PROVIDER": "fake",
    }
    out = subprocess.run(
        [sys.executable, "-c", PRINT_SETTINGS],
        cwd=settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()

    assert out == ["eld_e2e", "fake"]
