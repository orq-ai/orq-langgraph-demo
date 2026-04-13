"""Shared terminal helpers — colors + status markers.

Used by `doctor.py`, `setup_orq_workspace.py`, and the eval runners so the
same ✓/✗/→ style renders consistently across every CLI entry point.

Disable colors by setting `NO_COLOR=1` in the environment — respects the
[no-color.org](https://no-color.org/) convention.
"""

from __future__ import annotations

import os
import sys

# ANSI escape codes. Collapsed to empty strings when colors are off so the
# same f-string works in both modes without branching at every call site.
_COLORS_ON = sys.stdout.isatty() and os.environ.get("NO_COLOR") != "1"

GREEN = "\033[32m" if _COLORS_ON else ""
RED = "\033[31m" if _COLORS_ON else ""
YELLOW = "\033[33m" if _COLORS_ON else ""
BLUE = "\033[34m" if _COLORS_ON else ""
GRAY = "\033[90m" if _COLORS_ON else ""
BOLD = "\033[1m" if _COLORS_ON else ""
RESET = "\033[0m" if _COLORS_ON else ""


def green(text: str) -> str:
    return f"{GREEN}{text}{RESET}"


def red(text: str) -> str:
    return f"{RED}{text}{RESET}"


def yellow(text: str) -> str:
    return f"{YELLOW}{text}{RESET}"


def blue(text: str) -> str:
    return f"{BLUE}{text}{RESET}"


def gray(text: str) -> str:
    return f"{GRAY}{text}{RESET}"


def bold(text: str) -> str:
    return f"{BOLD}{text}{RESET}"


def check() -> str:
    """Green ✓."""
    return green("✓")


def cross() -> str:
    """Red ✗."""
    return red("✗")


def arrow() -> str:
    """Yellow → for remediation hints."""
    return yellow("→")


def ok(msg: str) -> None:
    """Print a green ✓ line."""
    print(f"{check()} {msg}")


def fail(msg: str, hint: str = "") -> None:
    """Print a red ✗ line, optionally followed by an indented hint."""
    print(f"{cross()} {msg}")
    if hint:
        print(f"  {arrow()} {hint}")


def warn(msg: str, hint: str = "") -> None:
    """Print a yellow ! line, optionally followed by an indented hint."""
    print(f"{yellow('!')} {msg}")
    if hint:
        print(f"  {arrow()} {hint}")


def section(title: str) -> None:
    """Print a bold section header with a leading blank line."""
    print(f"\n{bold(title)}")
