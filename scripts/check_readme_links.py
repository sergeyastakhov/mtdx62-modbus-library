"""Fail when a README link would break on the PyPI project page."""

from __future__ import annotations

import pathlib
import re
import sys

TARGET = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)")
ABSOLUTE_PREFIXES = ("https://", "http://", "mailto:", "#")


def main() -> int:
    """Report every link that is not absolute."""
    readme = pathlib.Path(__file__).resolve().parent.parent / "README.md"
    targets = TARGET.findall(readme.read_text(encoding="utf-8"))
    relative = [target for target in targets if not target.startswith(ABSOLUTE_PREFIXES)]
    if relative:
        print("relative links break the PyPI description; use absolute URLs:")
        for target in relative:
            print(f"  {target}")
        return 1
    print(f"{len(targets)} links checked, all absolute")
    return 0


if __name__ == "__main__":
    sys.exit(main())
