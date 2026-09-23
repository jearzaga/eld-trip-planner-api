from pathlib import Path

from django.core.management import call_command

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMITTED_OPENAPI_PATH = REPO_ROOT / "openapi.yaml"
REGENERATE_COMMAND = "uv run python manage.py spectacular --file openapi.yaml --validate"


def test_committed_openapi_yaml_matches_a_fresh_generation(tmp_path):
    generated_path = tmp_path / "openapi.yaml"
    call_command("spectacular", "--file", str(generated_path), "--validate")

    assert generated_path.read_text() == COMMITTED_OPENAPI_PATH.read_text(), (
        f"openapi.yaml is stale. Regenerate it with: {REGENERATE_COMMAND}"
    )
