import sys

from atc.commands.usage_error import USAGE_ERROR
from atc.commands.registry import resolve_command, usage_sections
from atc.ui.console import print_usage, error
from atc.core.config import ConfigError


# --- usage ---
def usage():
    print_usage(usage_sections())
    sys.exit(1)


# --- main ---
def main():
    if len(sys.argv) < 2:
        usage()
        
    spec = resolve_command(sys.argv[1])
    if not spec:
        usage()

    try:
        result = spec.handler(sys.argv[2:])
    except ConfigError as e:
        error(f"Error: {e}")
        sys.exit(1)

    if result is USAGE_ERROR:
        usage()
    if result is not None:
        sys.exit(result)

if __name__ == "__main__":
    main()
