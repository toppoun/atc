from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_VISUALIZER = PROJECT_ROOT / "tools" / "visualizer.html"
PACKAGE_VISUALIZER = PROJECT_ROOT / "atc" / "assets" / "visualizer.html"


def test_visualizer_assets_exist():
    assert TOOLS_VISUALIZER.is_file()
    assert PACKAGE_VISUALIZER.is_file()


def test_package_visualizer_matches_tools_visualizer():
    assert PACKAGE_VISUALIZER.read_bytes() == TOOLS_VISUALIZER.read_bytes()
