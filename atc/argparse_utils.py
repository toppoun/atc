import argparse


class ArgumentParseError(Exception):
    pass


class AtcArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("add_help", False)
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> None:
        raise ArgumentParseError(message)

    def exit(self, status=0, message=None) -> None:
        raise ArgumentParseError((message or "").strip())
