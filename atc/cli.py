import sys

from .commands import USAGE_ERROR, resolve_command, usage_sections
from .console import Table, Text, console


# --- Constants ---
TITLE_STYLE = "bold white"
SECTION_STYLE = "bold bright_blue"
COMMAND_STYLE = "cyan"
DESC_STYLE = "default"
NOTE_STYLE = "dim"

# --- usage ---
def usage():
    console.print(Text("AtC", style=TITLE_STYLE))
    for title, rows in usage_sections():
        console.print()
        console.print(Text(title, style=SECTION_STYLE))
        table = Table.grid(padding=(0, 4))
        table.add_column(no_wrap=True)
        table.add_column()
        for command, description in rows:
            table.add_row(Text(command, style=COMMAND_STYLE), Text(description, style=DESC_STYLE))
        console.print(table)
    console.print()
    console.print(Text("Tip: run `atc config doctor` to check your environment.", style=NOTE_STYLE))
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
