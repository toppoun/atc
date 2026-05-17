import random
import sys


def main() -> None:
    seed = int(sys.argv[1]) if len(sys.argv) >= 2 else None
    random.seed(seed)

    # TODO: 問題に合わせた出力に変更してください。
    n = random.randint(1, 8)
    a = [random.randint(0, 20) for _ in range(n)]

    print(n)
    print(*a)


if __name__ == "__main__":
    main()
