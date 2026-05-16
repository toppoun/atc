import pytest

from atc.visual import DEFAULT_LIVE_PREVIEW_URL, DEFAULT_PORT, parse_visual_args


def test_parse_visual_args_defaults():
    args = parse_visual_args([])

    assert args.port == DEFAULT_PORT
    assert args.open_browser is True
    assert args.live_preview is None
    assert args.live_preview_url == DEFAULT_LIVE_PREVIEW_URL
    assert args.fallback is True


def test_parse_visual_args_no_open():
    args = parse_visual_args(["--no-open"])

    assert args.open_browser is False


def test_parse_visual_args_port():
    assert parse_visual_args(["--port", "8765"]).port == 8765
    assert parse_visual_args(["--port=8766"]).port == 8766


def test_parse_visual_args_live_preview_modes():
    assert parse_visual_args(["--no-live-preview"]).live_preview is False
    assert parse_visual_args(["--live-preview"]).live_preview is True
    assert parse_visual_args(["--no-fallback"]).fallback is False


def test_parse_visual_args_live_preview_url():
    url = "http://127.0.0.1:3000/custom.html"

    assert parse_visual_args(["--live-preview-url", url]).live_preview_url == url
    assert parse_visual_args([f"--live-preview-url={url}"]).live_preview_url == url


@pytest.mark.parametrize("args", [["--port", "abc"], ["--port=0"], ["--port=70000"]])
def test_parse_visual_args_invalid_port(args):
    with pytest.raises(ValueError):
        parse_visual_args(args)


def test_parse_visual_args_unknown_option():
    with pytest.raises(ValueError):
        parse_visual_args(["--unknown"])


def test_parse_visual_args_conflicting_live_preview_options():
    with pytest.raises(ValueError):
        parse_visual_args(["--live-preview", "--no-live-preview"])
