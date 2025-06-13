#!/usr/bin/env python3
"""
src/commit.py - Commit-related functionality for the Arc Ninja Stack Tool
"""

import os
import sys
import tempfile

from src.utils import (
    apply_stash,
    check_changes,
    get_commit_hash_by_position,
    has_merge_conflicts,
    run_command,
    stash_changes,
)


def edit_nth_commit(position: int):
    """
    Edit the nth commit in the stack (counting from master).
    This will:
    1. Stash any staged and unstaged changes separately
    2. Start an interactive rebase to the selected commit
    3. Apply the staged changes
    4. Amend the commit
    5. Continue the rebase
    """
    # Check for staged and unstaged changes
    has_staged, has_unstaged = check_changes()

    if not (has_staged or has_unstaged):
        print("No changes to commit. Nothing to do.")
        sys.exit(0)

    # Stash unstaged changes first (if any)
    unstaged_stash = ""
    if has_unstaged:
        print("Stashing unstaged changes...")
        unstaged_stash = stash_changes("anist_unstaged_changes")

    # Stash staged changes (if any)
    staged_stash = ""
    if has_staged:
        print("Stashing staged changes...")
        staged_stash = stash_changes("anist_staged_changes")

    try:
        # Get the commit hash to edit
        target_commit = get_commit_hash_by_position(position)
        print(f"Targeting commit: {target_commit}")

        # Start an interactive rebase
        commit_range = f"{target_commit}^"  # Target's parent commit

        # Create a rebase script that changes only the target commit to 'edit'
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            rebase_script_path = temp_file.name

            # Get the rebase todo list
            rebase_todo = run_command(
                [
                    "git",
                    "rev-list",
                    "--reverse",
                    f"{commit_range}..HEAD",
                    "--format=%H %s",
                ],
                capture_output=True,
            ).stdout.strip()

            # Parse and modify the rebase todo
            lines = []
            for line in rebase_todo.split("\n"):
                if line.startswith("commit "):
                    continue

                if target_commit in line:
                    lines.append(f"edit {line}")
                else:
                    lines.append(f"pick {line}")

            # Write the modified rebase script
            temp_file.write("\n".join(lines))

        # Set the GIT_SEQUENCE_EDITOR to use our script
        editor_cmd = f"cat {rebase_script_path} >"
        os.environ["GIT_SEQUENCE_EDITOR"] = editor_cmd

        # Start the interactive rebase
        print(f"Starting interactive rebase to edit commit at position {position}...")
        run_command(["git", "rebase", "-i", commit_range])

        # Cleanup the temp file
        os.remove(rebase_script_path)

        # Apply the staged changes first if we had any
        if has_staged:
            print("Applying staged changes...")
            apply_stash(staged_stash)

            # Check if there were merge conflicts
            if has_merge_conflicts():
                print("\nMerge conflicts detected!")
                print("Please resolve the conflicts, then run:")
                print("  git add <resolved_files>")
                print("  git commit --amend")
                print("  git rebase --continue")

                # Also apply unstaged changes if there were any
                if has_unstaged:
                    print("\nAttempting to apply your unstaged changes as well...")
                    apply_stash(unstaged_stash)
                    print("Your unstaged changes have been applied.")

                sys.exit(1)

            # Stage all changes
            run_command(["git", "add", "-u"])

            # Amend the commit
            print("Amending the commit...")
            run_command(["git", "commit", "--amend", "--no-edit"])

            # Continue the rebase
            print("Continuing the rebase...")
            run_command(["git", "rebase", "--continue"])

        # Apply unstaged changes if we had any (after rebase is complete)
        if has_unstaged:
            print("Applying unstaged changes...")
            apply_stash(unstaged_stash)
            print("Your unstaged changes have been applied.")

        print("\nRebase successfully completed!")

    except Exception as e:
        print(f"Error during rebase: {e}")

        # Try to restore stashed changes if there was an error
        if has_unstaged:
            print("Attempting to restore unstaged changes...")
            apply_stash(unstaged_stash)

        if has_staged:
            print("Attempting to restore staged changes...")
            apply_stash(staged_stash)

        print("Check 'git status' to see the current state.")
        sys.exit(1)
