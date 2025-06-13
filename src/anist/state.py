#!/usr/bin/env python3
"""
src/anist/state.py - Application state management for the Arc Ninja Stack Tool
"""

from rich import print as rprint


# Application global state
class AppState:
    """Global application state class."""

    def __init__(self):
        self.quiet = False


# Single global instance to share across modules
app_state = AppState()


def set_quiet(value: bool) -> None:
    """Set the quiet flag in the application state."""
    app_state.quiet = value


def is_quiet() -> bool:
    """Check if quiet mode is enabled."""
    return app_state.quiet


def print_if_not_quiet(message: str) -> None:
    """Print a message only if not in quiet mode."""
    if not app_state.quiet:
        print(message)


def rich_print_if_not_quiet(message: str) -> None:
    """Print a rich-formatted message only if not in quiet mode."""
    if not app_state.quiet:
        rprint(message)
