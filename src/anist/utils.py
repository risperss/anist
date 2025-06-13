#!/usr/bin/env python3
"""
src/utils.py - Utility functions for the Arc Ninja Stack Tool
"""

import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

from anist.state import is_quiet


def run_command(
    cmd: List[str], cwd: Optional[str] = None, capture_output: bool = False
) -> subprocess.CompletedProcess:
    """Run a shell command and handle errors."""
    try:
        # If we're capturing output or in quiet mode, use capture_output=True
        should_capture = capture_output or is_quiet()

        result = subprocess.run(
            cmd, cwd=cwd, check=True, text=True, capture_output=should_capture
        )
        return result
    except subprocess.CalledProcessError as e:
        # Always show errors, even in quiet mode
        print(f"Error executing command: {' '.join(cmd)}")
        print(f"Exit code: {e.returncode}")
        if e.stdout:
            print(f"Standard output:\n{e.stdout}")
        if e.stderr:
            print(f"Standard error:\n{e.stderr}")
        sys.exit(e.returncode)


def get_current_branch() -> str:
    """Get the name of the current git branch."""
    result = run_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True
    )
    return result.stdout.strip()


def get_commit_hash_by_position(position: int) -> str:
    """
    Get the commit hash at position n from master.
    Position 1 is the first commit after master.
    """
    result = run_command(
        ["git", "rev-list", "--reverse", "master..HEAD"], capture_output=True
    )
    commit_hashes = result.stdout.strip().split("\n")

    if not commit_hashes or commit_hashes[0] == "":
        print("Error: No commits found between master and HEAD")
        sys.exit(1)

    if position < 1 or position > len(commit_hashes):
        print(
            f"Error: Position {position} is out of range. Valid range is 1 to {len(commit_hashes)}."
        )
        sys.exit(1)

    return commit_hashes[position - 1]


def get_all_commits_in_stack() -> List[str]:
    """
    Get all commit hashes in the current stack (from master to HEAD).
    Returns a list of commit hashes, with the oldest commit (first after master) first.
    """
    result = run_command(
        ["git", "rev-list", "--reverse", "master..HEAD"], capture_output=True
    )
    commit_hashes = result.stdout.strip().split("\n")

    if not commit_hashes or commit_hashes[0] == "":
        print("Error: No commits found between master and HEAD")
        sys.exit(1)

    return commit_hashes


def get_commit_count_in_stack() -> int:
    """Get the number of commits in the current stack."""
    return len(get_all_commits_in_stack())


def check_changes() -> Tuple[bool, bool]:
    """
    Check for staged and unstaged changes.
    Returns a tuple of (has_staged_changes, has_unstaged_changes)
    """
    # Check for staged changes
    staged_changes = run_command(
        ["git", "diff", "--name-only", "--cached"], capture_output=True
    ).stdout.strip()
    has_staged = bool(staged_changes)

    # Check for unstaged changes
    unstaged_changes = run_command(
        ["git", "diff", "--name-only"], capture_output=True
    ).stdout.strip()
    has_unstaged = bool(unstaged_changes)

    return (has_staged, has_unstaged)


def stash_changes(message: str) -> str:
    """
    Stash changes with the given message and return the stash hash.
    Returns empty string if no changes were stashed.
    """
    # First check if there are any changes to stash
    status_result = run_command(["git", "status", "--porcelain"], capture_output=True)
    if not status_result.stdout.strip():
        return ""  # No changes to stash

    # Create a stash
    stash_result = run_command(
        ["git", "stash", "create", message], capture_output=True
    ).stdout.strip()

    if not stash_result:
        return ""  # No stash was created

    # Store the stash with a reference
    run_command(["git", "stash", "store", "-m", message, stash_result])

    # Clean the working directory
    run_command(["git", "reset", "--hard", "HEAD"])

    return stash_result


def apply_stash(stash_ref: str) -> bool:
    """
    Apply and drop a specific stash. Returns True if successful.
    """
    if not stash_ref:
        return False

    try:
        # Find the stash index by its hash
        stash_list = run_command(
            ["git", "stash", "list", "--format=%H %gd"], capture_output=True
        )
        stash_index = None

        for line in stash_list.stdout.strip().split("\n"):
            if line and stash_ref in line:
                parts = line.split()
                if len(parts) > 1:
                    stash_index = parts[1]
                    break

        if stash_index:
            run_command(["git", "stash", "apply", stash_index])
            run_command(["git", "stash", "drop", stash_index])
            return True
        return False
    except Exception:
        print(f"Warning: Failed to apply stash {stash_ref}")
        return False


def find_commit_position_by_message(message: str) -> int:
    """
    Find the position of a commit in the stack based on its message.
    Returns the position (1-based) or 0 if not found.
    """
    if not message:
        return 0

    try:
        # Get all commits in the stack
        result = run_command(
            ["git", "rev-list", "--reverse", "master..HEAD", "--format=%s"],
            capture_output=True,
        )
        lines = result.stdout.strip().split("\n")

        # Filter out the "commit <hash>" lines
        commit_messages = [line for line in lines if not line.startswith("commit ")]

        # Look for a commit message that contains the arc diff message
        # Normalize the message by removing leading/trailing whitespace and lowercase
        normalized_message = message.strip().lower()
        for i, commit_msg in enumerate(commit_messages):
            if normalized_message in commit_msg.strip().lower():
                return i + 1  # 1-based indexing

        return 0
    except Exception as e:
        print(f"Error finding commit position: {e}")
        return 0


def get_diff_ids() -> Dict[int, str]:
    """
    Parse the output of 'arc list' to get the mapping of commit positions to diff IDs.
    Returns a dictionary mapping commit positions to diff IDs.
    """
    try:
        # Run arc list to get all diffs
        result = run_command(["arc", "list"], capture_output=True)
        lines = result.stdout.strip().split("\n")

        # Parse the output to extract diff IDs
        diff_ids = {}
        for line in lines:
            # Match the diff ID (e.g., D28944)
            match = re.search(r"D(\d+)", line)
            if match:
                diff_id = match.group(0)

                # Get the commit message for this diff
                commit_message = line.split(":", 1)[1].strip() if ":" in line else ""

                # Try to find a commit in our stack that matches this commit message
                commit_position = find_commit_position_by_message(commit_message)
                if commit_position > 0:
                    diff_ids[commit_position] = diff_id

        return diff_ids
    except Exception as e:
        print(f"Error getting diff IDs: {e}")
        return {}


def find_diff_id_in_commit(commit_hash: str) -> Optional[str]:
    """
    Parse the diff ID from a commit message.
    Returns the diff ID (e.g., D12345) or None if not found.
    """
    try:
        # Look for "Differential Revision: Dxxxxx" in the commit message
        commit_message = run_command(
            ["git", "log", "-1", commit_hash], capture_output=True
        ).stdout
        diff_match = re.search(r"Differential Revision:.*(D\d+)", commit_message)
        if diff_match:
            return diff_match.group(1)
        return None
    except Exception:
        return None


def get_commit_message(commit_hash: str) -> str:
    """Get the short commit message for a commit."""
    try:
        return run_command(
            ["git", "log", "-1", "--format=%s", commit_hash], capture_output=True
        ).stdout.strip()
    except Exception:
        return ""


def has_merge_conflicts() -> bool:
    """Check if there are merge conflicts."""
    status = run_command(["git", "status", "--porcelain"], capture_output=True).stdout
    return any(line.startswith(("UU", "AA", "DD")) for line in status.split("\n"))
