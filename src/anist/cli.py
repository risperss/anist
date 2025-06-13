#!/usr/bin/env python3
"""
src/cli.py - Command-line interface for the Arc Ninja Stack Tool using Typer
"""

import sys

import typer
from rich import print as rprint

from anist.commit import edit_nth_commit
from anist.diff import update_diff_command
from anist.state import rich_print_if_not_quiet, set_quiet

app = typer.Typer(help="Anist - Arc Ninja Stack Tool for managing stacked diffs")
commit_app = typer.Typer(help="Edit a commit in the stack")
diff_app = typer.Typer(help="Create or update diffs for commits")

# Add sub-commands to the main app
app.add_typer(commit_app, name="commit")
app.add_typer(diff_app, name="diff")


# Add callback for the main app to handle global options
@app.callback()
def global_options(
    quiet: bool = typer.Option(
        False, "--quiet", help="Suppress output from subcommands, except errors"
    ),
):
    """Configure global CLI options."""
    set_quiet(quiet)


@commit_app.callback(invoke_without_command=True)
def commit_main(
    position: int = typer.Option(
        ..., "-n", "--number", help="Position of the commit to edit"
    ),
):
    """Edit a specific commit in the stack."""
    rich_print_if_not_quiet(
        f"[bold blue]Editing commit at position {position}...[/bold blue]"
    )
    edit_nth_commit(position)


@diff_app.callback(invoke_without_command=True)
def diff_main(
    position: int = typer.Option(
        1, "-n", "--number", help="Position of the commit to process"
    ),
    message: str = typer.Option(
        "anist default message", "-m", "--message", help="Update message for the diff"
    ),
    create: bool = typer.Option(
        False, "--create", help="Create a new diff instead of updating"
    ),
    full_stack: bool = typer.Option(
        False, "--full-stack", help="Process all commits in the stack"
    ),
):
    """Create or update diffs for commits."""
    if full_stack:
        rich_print_if_not_quiet(
            "[bold blue]Processing all commits in the stack...[/bold blue]"
        )
    else:
        rich_print_if_not_quiet(
            f"[bold blue]Processing commit at position {position}...[/bold blue]"
        )

    update_diff_command(position, message, create, full_stack)


def main():
    """Main entry point for the command-line interface."""
    try:
        return app()
    except Exception as e:
        rprint(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
