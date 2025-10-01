from __future__ import annotations

import argparse
from pathlib import Path

from app.gui import run_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="游戏商城自动助手")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path.home() / ".dfshoper" / "config.json",
        help="配置文件路径",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_app(args.config)


if __name__ == "__main__":
    main()
