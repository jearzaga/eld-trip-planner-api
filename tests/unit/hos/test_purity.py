import ast
import sys
from pathlib import Path

HOS_DIR = Path(__file__).resolve().parents[3] / "hos"


def imported_top_level_modules(source_file: Path) -> set[str]:
    tree = ast.parse(source_file.read_text())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def test_hos_package_has_modules_to_check():
    assert (HOS_DIR / "models.py").exists()


def test_hos_imports_only_the_standard_library():
    allowed = sys.stdlib_module_names | {"hos"}
    offenders = {
        source_file.name: sorted(imported_top_level_modules(source_file) - allowed)
        for source_file in HOS_DIR.glob("*.py")
    }
    assert {name: bad for name, bad in offenders.items() if bad} == {}
