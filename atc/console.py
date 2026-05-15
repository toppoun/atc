RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def color_text(message: str, color: str) -> str:
    return f"{color}{message}{RESET}"


def ok(message: str) -> None:
    print(color_text(message, GREEN))


def warn(message: str) -> None:
    print(color_text(message, YELLOW))


def error(message: str) -> None:
    print(color_text(message, RED))
