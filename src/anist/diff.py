#!/usr/bin/env python3
"""
src/diff.py - Diff-related functionality for the Arc Ninja Stack Tool
"""

from anist.state import print_if_not_quiet
from anist.utils import (
    apply_stash,
    check_changes,
    find_diff_id_in_commit,
    get_all_commits_in_stack,
    get_commit_hash_by_position,
    get_commit_message,
    get_current_branch,
    get_diff_ids,
    run_command,
    stash_changes,
)


def create_or_update_diff(
    position: int, message: str, create_mode: bool = False
) -> bool:
    """
    Create or update the Phabricator diff for the commit at the given position.

    Args:
        position: Position of the commit in the stack (1 = first commit after master)
        message: Update message for the diff
        create_mode: If True, create a new diff instead of updating

    Returns:
        True if successful, False otherwise
    """
    # First, check if we have uncommitted changes
    has_staged, has_unstaged = check_changes()

    # Stash any changes to keep the working directory clean
    unstaged_stash = ""
    if has_unstaged:
        print_if_not_quiet("Stashing unstaged changes...")
        unstaged_stash = stash_changes("anist_unstaged_changes_diff")

    staged_stash = ""
    if has_staged:
        print_if_not_quiet("Stashing staged changes...")
        staged_stash = stash_changes("anist_staged_changes_diff", staged_only=True)

    try:
        # Get the commit hash for the specified position
        commit_hash = get_commit_hash_by_position(position)
        print_if_not_quiet(f"Targeting commit at position {position}: {commit_hash}")

        # Get the short commit message for this commit
        commit_msg = get_commit_message(commit_hash)
        print_if_not_quiet(f"Commit message: {commit_msg}")

        # Get the current branch and store it
        original_branch = get_current_branch()

        # Checkout the specific commit
        print_if_not_quiet(f"Checking out commit {commit_hash}...")
        run_command(["git", "checkout", commit_hash])

        # Try to find the diff ID for this commit if we're not in create mode
        diff_id = None
        if not create_mode:
            # Method 1: Check arc list output and match with commit position
            diff_ids = get_diff_ids()
            if position in diff_ids:
                diff_id = diff_ids[position]
                print_if_not_quiet(f"Found diff ID for position {position}: {diff_id}")

            # Method 2: Parse from the commit message if available
            if not diff_id:
                diff_id = find_diff_id_in_commit(commit_hash)
                if diff_id:
                    print_if_not_quiet(f"Found diff ID in commit message: {diff_id}")

            if not diff_id:
                print(
                    "Could not determine the diff ID. Either use --create to create a new diff or specify a diff ID manually."
                )
                run_command(["git", "checkout", original_branch])
                return False

        # Build the arc diff command
        if create_mode:
            print_if_not_quiet("Creating new diff...")
            diff_cmd = ["arc", "diff", "HEAD~1"]
        else:
            print_if_not_quiet(f"Updating {diff_id}...")
            diff_cmd = ["arc", "diff", "HEAD~1", "--update", diff_id]

        # Add message if provided
        if message:
            diff_cmd.extend(["--message", message])

        # Run the arc diff command
        run_command(diff_cmd)

        # Return to the original branch
        print_if_not_quiet(f"Returning to branch {original_branch}...")
        run_command(["git", "checkout", original_branch])

        if create_mode:
            print_if_not_quiet("Successfully created new diff!")
        else:
            print_if_not_quiet(f"Successfully updated diff {diff_id}!")

        return True

    except Exception as e:
        print(f"Error {'creating' if create_mode else 'updating'} diff: {e}")
        return False
    finally:
        # Restore any stashed changes
        if has_staged:
            print_if_not_quiet("Restoring staged changes...")
            apply_stash(staged_stash, keep_index=True)
        if has_unstaged:
            print_if_not_quiet("Restoring unstaged changes...")
            apply_stash(unstaged_stash, keep_index=False)


def update_diff_stack(message: str, create_mode: bool = False):
    """
    Update or create diffs for all commits in the stack.
    Exits on first error.

    Args:
        message: Update message for all diffs
        create_mode: If True, create new diffs instead of updating
    """
    # Get all commits in the stack
    commits = get_all_commits_in_stack()

    if not commits:
        print("No commits found in the stack.")
        return

    print_if_not_quiet(f"Found {len(commits)} commit(s) in the stack.")

    success_count = 0

    for i, _ in enumerate(commits):
        position = i + 1  # 1-based indexing
        print_if_not_quiet(
            f"\n[{position}/{len(commits)}] Processing commit at position {position}..."
        )

        if create_or_update_diff(position, message, create_mode):
            success_count += 1
        else:
            print_if_not_quiet(
                f"Error encountered with diff at position {position}. Stopping."
            )
            print_if_not_quiet(
                f"\nStack diff update stopped: {success_count} successful, 1 failed."
            )
            return

    print_if_not_quiet(
        f"\nStack diff update complete: {success_count} successful, 0 failed."
    )


def update_diff_command(
    position: int, message: str, create: bool = False, full_stack: bool = False
):
    """
    Main entry point for the diff command.

    Args:
        position: Position of the commit (1-based)
        message: Update message
        create: If True, create new diffs instead of updating
        full_stack: If True, process all commits in the stack
    """
    if full_stack:
        update_diff_stack(message, create)
    else:
        create_or_update_diff(position, message, create)
