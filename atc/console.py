RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def ok(message: str) -> None:
    print(f"{GREEN}{message}{RESET}")


def warn(message: str) -> None:
    print(f"{YELLOW}{message}{RESET}")


def error(message: str) -> None:
    print(f"{RED}{message}{RESET}")
