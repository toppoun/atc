from typing import List

from atc.argparse_utils import AtcArgumentParser, ArgumentParseError
from atc.ui.console import error # 削除候補


# --- Argument parsing helpes ---
def parse_handler_args(parser: AtcArgumentParser, args: List[str]):
    try:
        return parser.parse_args(args)
    except ArgumentParseError as e:
        if str(e):
            error(f"Error: {e}")
        return None