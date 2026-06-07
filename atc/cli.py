import sys

from atc.commands.registry import USAGE_ERROR, resolve_command


# --- usage ---
def usage():

    sys.exit(1)


# --- main ---
def main():
    if len(sys.argv) < 2:
        usage()
    spec = resolve_command(sys.argv[1])
    if not spec:
        usage()

    result = spec.handler(sys.argv[2:])
    if result is USAGE_ERROR:
        usage()
    if result is not None:
        sys.exit(result)

if __name__ == "__main__":
    main()
