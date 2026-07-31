from pathlib import Path
from typing import List, Sequence

from atc.core.config import (
    ConfigError,
    cpp_library_path,
    runner_cpp_debug_flags,
    runner_cpp_flags,
)

BUILTIN_CPP_INCLUDE_DIR = (
    Path(__file__).resolve().parents[1]
    / "resources"
    / "cpp"
    / "include"
)
BUILTIN_CPP_DEBUG_HEADER = (
    BUILTIN_CPP_INCLUDE_DIR
    / "atc"
    / "debug.hpp"
)


def build_cpp_compile_flags(
    config: dict,
    cwd: Path,
    *,
    debug: bool = False,
    extra_flags: Sequence[str] = (),
) -> List[str]:
    flags = list(runner_cpp_flags(config))

    library_path = cpp_library_path(config, cwd)
    if library_path is not None:
        if not library_path.exists():
            raise ConfigError(f"C++ library directory not found: {library_path}")
        if not library_path.is_dir():
            raise ConfigError(f"C++ library path is not a directory: {library_path}")
        flags.extend(["-I", str(library_path)])

    if debug:
        if not BUILTIN_CPP_DEBUG_HEADER.is_file():
            raise ConfigError(
                f"Built-in C++ debug header not found: "
                f"{BUILTIN_CPP_DEBUG_HEADER}. Reinstall atc."
            )
        flags.extend(["-I", str(BUILTIN_CPP_INCLUDE_DIR)])
        flags.extend(runner_cpp_debug_flags(config))

    flags.extend(str(flag) for flag in extra_flags)
    return flags
