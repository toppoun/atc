import functools
import http.server
import socket
import sys
import webbrowser
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


DEFAULT_PORT = 8765
HOST = "127.0.0.1"
VISUALIZER_NAME = "visualizer.html"


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


def _print_not_found_error(error: VisualizerNotFoundError):
    print("ERROR: visualizer.html was not found.")
    print()
    print("Tried:")
    for path in error.tried:
        print(f"  - {path}")
    print()
    print("Please make sure tools/visualizer.html exists.")


def cmd_visual(port: int = DEFAULT_PORT, open_browser: bool = True) -> int:
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
        try:
            webbrowser.open(url)
        except Exception as error:  # pragma: no cover - webbrowser is environment-dependent
            print(f"Warning: failed to open browser automatically: {error}", file=sys.stderr)
            print("Open the URL above manually.", file=sys.stderr)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nvisualizer stopped.")
    finally:
        server.server_close()
    return 0


def parse_visual_args(args: List[str]) -> Tuple[int, bool]:
    port = DEFAULT_PORT
    open_browser = True
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--no-open":
            open_browser = False
            i += 1
            continue
        if arg == "--port":
            if i + 1 >= len(args):
                raise ValueError("--port requires a number.")
            i += 1
            try:
                port = int(args[i])
            except ValueError:
                raise ValueError("--port requires a number.")
            if port < 1 or port > 65535:
                raise ValueError("--port must be between 1 and 65535.")
            i += 1
            continue
        if arg.startswith("--port="):
            value = arg.split("=", 1)[1]
            try:
                port = int(value)
            except ValueError:
                raise ValueError("--port requires a number.")
            if port < 1 or port > 65535:
                raise ValueError("--port must be between 1 and 65535.")
            i += 1
            continue
        raise ValueError(f"unknown option for atc visual: {arg}")
    return port, open_browser
