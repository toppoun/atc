import functools
import http.server
import socket
import sys
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


# --- Constants ---
DEFAULT_PORT = 8765
HOST = "127.0.0.1"
VISUALIZER_NAME = "visualizer.html"
DEFAULT_LIVE_PREVIEW_URL = "http://127.0.0.1:3000/tools/visualizer.html?vscode-livepreview=true"


@dataclass
class VisualArgs:
    port: int = DEFAULT_PORT
    open_browser: bool = True
    live_preview: Optional[bool] = None
    live_preview_url: str = DEFAULT_LIVE_PREVIEW_URL
    fallback: bool = True


class VisualizerNotFoundError(Exception):
    def __init__(self, tried: Iterable[Path]):
        self.tried = list(tried)
        super().__init__("visualizer.html was not found")


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - matches stdlib signature
        return


def _project_root_from(start: Path) -> Optional[Path]:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for directory in (current, *current.parents):
        if (
            (directory / ".git").exists()
            or (directory / "pyproject.toml").exists()
            or (directory / ".atc").exists()
        ):
            return directory
    return None


def _find_visualizer_html(start: Optional[Path] = None) -> Tuple[Path, List[Path]]:
    start = (start or Path.cwd()).resolve()
    tried: List[Path] = []

    candidates = [start / "tools" / VISUALIZER_NAME]
    project_root = _project_root_from(start)
    if project_root is not None:
        candidates.append(project_root / "tools" / VISUALIZER_NAME)

    module_file = Path(__file__).resolve()
    candidates.append(module_file.parents[1] / "tools" / VISUALIZER_NAME)
    candidates.append(module_file.parent / "assets" / VISUALIZER_NAME)

    seen = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        tried.append(candidate)
        if candidate.is_file():
            return candidate, tried

    raise VisualizerNotFoundError(tried)


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((HOST, port))
        except OSError:
            return False
    return True


def _find_free_port(preferred_port: int, attempts: int = 20) -> int:
    last_port = min(65535, preferred_port + attempts - 1)
    for port in range(preferred_port, last_port + 1):
        if _port_available(port):
            return port
    raise OSError(f"No free port found in {preferred_port}..{last_port}.")


def _serve_directory(directory: Path, port: int) -> http.server.ThreadingHTTPServer:
    handler = functools.partial(QuietHTTPRequestHandler, directory=str(directory))
    return http.server.ThreadingHTTPServer((HOST, port), handler)


def _is_url_available(url: str, timeout: float = 0.8) -> bool:
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


def _print_not_found_error(error: VisualizerNotFoundError):
    print("ERROR: visualizer.html was not found.")
    print()
    print("Tried:")
    for path in error.tried:
        print(f"  - {path}")
    print()
    print("Please make sure tools/visualizer.html exists.")


def _open_url(url: str):
    try:
        webbrowser.open(url)
    except Exception as error:  # pragma: no cover - webbrowser is environment-dependent
        print(f"Warning: failed to open browser automatically: {error}", file=sys.stderr)
        print("Open the URL above manually.", file=sys.stderr)


def _open_live_preview(url: str, open_browser: bool) -> int:
    if open_browser:
        print("Opening AtCoder Visualizer via VS Code Live Preview:")
        print(f"  {url}")
        _open_url(url)
    else:
        print("VS Code Live Preview seems available.")
        print()
        print("URL:")
        print(f"  {url}")
        print()
        print("Browser was not opened because --no-open was specified.")
    return 0


def _run_local_server(port: int = DEFAULT_PORT, open_browser: bool = True) -> int:
    try:
        visualizer_html, _tried = _find_visualizer_html()
    except VisualizerNotFoundError as error:
        _print_not_found_error(error)
        return 1

    try:
        actual_port = _find_free_port(port)
        server = _serve_directory(visualizer_html.parent, actual_port)
    except OSError as error:
        print(f"ERROR: failed to start visualizer server: {error}")
        return 1

    url = f"http://{HOST}:{actual_port}/{VISUALIZER_NAME}"
    print("AtCoder Visualizer is running.")
    print()
    print("URL:")
    print(f"  {url}")
    if actual_port != port:
        print()
        print(f"Note: port {port} was unavailable, so port {actual_port} is used.")
    print()
    print("Press Ctrl+C to stop.")
    print(flush=True)

    if open_browser:
        _open_url(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nvisualizer stopped.")
    finally:
        server.server_close()
    return 0


def cmd_visual(
    port: int = DEFAULT_PORT,
    open_browser: bool = True,
    live_preview: Optional[bool] = None,
    live_preview_url: str = DEFAULT_LIVE_PREVIEW_URL,
    fallback: bool = True,
) -> int:
    if live_preview is False:
        print("Skipping VS Code Live Preview.")
        print("Starting local server.")
        print()
        return _run_local_server(port=port, open_browser=open_browser)

    if _is_url_available(live_preview_url):
        return _open_live_preview(live_preview_url, open_browser=open_browser)

    if not fallback:
        print("ERROR: VS Code Live Preview was not available.")
        print()
        print("URL:")
        print(f"  {live_preview_url}")
        print()
        print("Start VS Code Live Preview or run: atc vis --no-live-preview")
        return 1

    print("VS Code Live Preview was not available.")
    print("Starting local server instead.")
    print()
    return _run_local_server(port=port, open_browser=open_browser)


def _parse_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError:
        raise ValueError("--port requires a number.")
    if port < 1 or port > 65535:
        raise ValueError("--port must be between 1 and 65535.")
    return port


def parse_visual_args(args: List[str]) -> VisualArgs:
    parsed = VisualArgs()
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--no-open":
            parsed.open_browser = False
            i += 1
            continue
        if arg == "--live-preview":
            if parsed.live_preview is False:
                raise ValueError("--live-preview and --no-live-preview cannot be used together.")
            parsed.live_preview = True
            i += 1
            continue
        if arg == "--no-live-preview":
            if parsed.live_preview is True:
                raise ValueError("--live-preview and --no-live-preview cannot be used together.")
            parsed.live_preview = False
            i += 1
            continue
        if arg == "--no-fallback":
            parsed.fallback = False
            i += 1
            continue
        if arg == "--live-preview-url":
            if i + 1 >= len(args):
                raise ValueError("--live-preview-url requires a URL.")
            i += 1
            if not args[i]:
                raise ValueError("--live-preview-url requires a URL.")
            parsed.live_preview_url = args[i]
            i += 1
            continue
        if arg.startswith("--live-preview-url="):
            value = arg.split("=", 1)[1]
            if not value:
                raise ValueError("--live-preview-url requires a URL.")
            parsed.live_preview_url = value
            i += 1
            continue
        if arg == "--port":
            if i + 1 >= len(args):
                raise ValueError("--port requires a number.")
            i += 1
            parsed.port = _parse_port(args[i])
            i += 1
            continue
        if arg.startswith("--port="):
            value = arg.split("=", 1)[1]
            parsed.port = _parse_port(value)
            i += 1
            continue
        raise ValueError(f"unknown option for atc visual: {arg}")
    return parsed
