# Anist - Arc Ninja Stack Tool

> Anist is a command-line tool designed to streamline workflows with stacked diffs in Phabricator and Arcanist. It provides advanced automation for common tasks when working with stacked commits, allowing developers to focus on code rather than managing version control processes.

## Table of Contents

- [Installation](#installation)
  - [Using uv (Recommended)](#using-uv-recommended)
  - [Using pip](#using-pip)
  - [From Source](#from-source)
- [Commands](#commands)
  - [commit - Edit Commits in a Stack](#commit---edit-commits-in-a-stack)
  - [diff - Manage Phabricator Diffs](#diff---manage-phabricator-diffs)
- [Use Cases](#use-cases)
- [Technical Details](#technical-details)
- [Tips and Tricks](#tips-and-tricks)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Installation

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a faster, more reliable Python package installer and resolver:

```bash
# Install anist using uv
uv pip install git+https://github.com/gaetanorispoli/anist.git

# Or, if you've cloned the repo
cd ~/repos/anist
uv pip install -e .
```

### Using pip

```bash
# Install directly from GitHub
pip install git+https://github.com/gaetanorispoli/anist.git

# Or, if you've cloned the repo
cd ~/repos/anist
pip install -e .
```

### From Source

1. Clone the repository
   ```bash
   git clone https://github.com/gaetanorispoli/anist.git
   cd ~/repos/anist
   ```

2. Install the package
   ```bash
   # Using uv
   uv pip install -e .

   # Using pip
   pip install -e .
   ```

After installation, the `anist` command will be available from any directory.

## Commands

Anist uses a modern CLI interface built with [Typer](https://typer.tiangolo.com/), offering rich help text and intuitive command structure with colorful output.

### commit - Edit Commits in a Stack

The `commit` command automates the process of editing a specific commit in a stack of commits.

#### Syntax

```
anist commit -n <position>
```

#### Parameters

- `-n, --number` - Position of the commit to edit (1 = first commit after master)

#### What It Does

1. Stashes any unstaged changes
2. Stashes any staged changes
3. Automatically performs an interactive rebase to the specified commit
4. Applies your previously staged changes to the target commit
5. Automatically stages, amends, and continues the rebase
6. Restores any unstaged changes

#### Examples

**Edit the second commit in your stack:**
```bash
anist commit -n 2
```

**Make changes to your first commit:**
```bash
anist commit -n 1
```

### diff - Manage Phabricator Diffs

The `diff` command creates or updates Phabricator diffs for specific commits or entire stacks.

#### Syntax

```
anist diff [OPTIONS]
```

#### Parameters

- `-n, --number` - Position of the commit to process (1 = first commit after master) [default: 1]
- `-m, --message` - Update message for the diff [default: "anist default message"]
- `--create` - Create a new diff instead of updating an existing one
- `--full-stack` - Process all commits in the stack

#### What It Does

1. Safely stashes any uncommitted changes
2. For each targeted commit:
   - Checks out the commit
   - Finds the corresponding diff ID (if updating)
   - Runs appropriate arc commands
   - Returns to the original branch
3. Restores any stashed changes

#### Examples

**Update the diff for the third commit in your stack:**
```bash
anist diff -n 3 -m "Fixed validation logic"
```

**Create a new diff for the first commit:**
```bash
anist diff -n 1 --create -m "Initial implementation"
```

**Update all diffs in your stack:**
```bash
anist diff --full-stack -m "Address code review feedback"
```

**Create new diffs for all commits in your stack:**
```bash
anist diff --full-stack --create -m "New feature implementation"
```

## Use Cases

### Implementing a Multi-Commit Feature

When working on a large feature that's split into several logical commits:

1. Create your stack of commits normally
2. Use `anist diff --full-stack --create` to submit the entire stack for review
3. When you receive feedback on a specific commit:
   - Use `anist commit -n <position>` to make changes to that commit
   - Use `anist diff -n <position>` to update just that diff

### Making Changes in the Middle of a Stack

If you need to make changes to a commit in the middle of your stack:

1. Stage your changes (`git add <files>`)
2. Run `anist commit -n <position>`
3. The tool will automatically handle the complex rebase process
4. Run `anist diff -n <position>` to update the corresponding diff

### Updating Multiple Diffs at Once

After addressing review feedback across multiple commits:

```bash
anist diff --full-stack -m "Address code review feedback"
```

This updates all diffs in your stack with a single command.

## Technical Details

### How Commit Editing Works

The `commit` command:

1. Uses Git's interactive rebase feature with custom automation
2. Creates a temporary rebase script that marks only your target commit for editing
3. Properly stashes both staged and unstaged changes separately, maintaining their status
4. Applies staged changes with `--index` to keep them staged during amend
5. Automatically continues the rebase when changes are applied successfully
6. Reapplies unstaged changes after the rebase is complete

### How Diff Management Works

The `diff` command:

1. Uses two methods to identify the correct diff for a commit:
   - Parses `arc list` output to match commit messages with diff descriptions
   - Looks for "Differential Revision: D123" in commit messages
2. Handles checkout and restoration of your workspace state
3. Uses Arcanist's API for creating and updating diffs

### Conflict Handling

If merge conflicts occur during a commit edit:

1. The tool will pause the automation
2. Notify you of conflicts
3. Apply your unstaged changes (if any)
4. Let you resolve conflicts manually
5. Provide instructions for completing the process

## Tips and Tricks

### Working with Complex Stacks

For stacks with many commits, use `--full-stack` with care:

```bash
# First update just the first commit
anist diff -n 1 -m "Fix core logic"

# Then, if that looks good, update the rest
anist diff --full-stack -m "Update dependent changes"
```

### Creating a New Stack from Existing Commits

If you have a stack of commits that haven't been submitted to Phabricator:

```bash
# Create diffs for all commits in the stack
anist diff --full-stack --create
```

### Updating a Single Diff After a Complex Change

After making changes that affect multiple files within a single commit:

```bash
# Stage all changes
git add -u

# Apply to specific commit
anist commit -n 3

# Update the diff
anist diff -n 3 -m "Refactored authentication logic"
```

## Troubleshooting

### Changes Not Maintaining Staged/Unstaged Status

If you notice that your staged changes become unstaged after running `anist commit`:

1. Make sure you're using the latest version of `anist` which properly preserves staging status
2. You can always re-stage the changes with `git add <files>` if needed
3. The improved stash handling now correctly maintains the staged vs. unstaged status of files

### Error: "Could not determine the diff ID"

When updating a diff and anist can't find the corresponding diff ID:

1. Check that the diff exists with `arc list`
2. Ensure the commit message is similar to the diff title
3. If needed, use `--create` to create a new diff instead

### Error During Rebase

If the automatic rebase encounters problems:

1. The tool will attempt to restore your working state
2. Check `git status` to see the current state
3. Either resolve conflicts or run `git rebase --abort`
4. Try again with smaller changes

### Stash Recovery

If the tool crashes or encounters an unrecoverable error:

1. Check your stash list with `git stash list`
2. Look for entries with "anist" in their description
3. Apply them with `git stash apply stash@{n}`

### Using From Different Repositories

Anist is installed globally, so you can use it in any Git repository:

1. Make sure you're in the root directory of your Git repository
2. Run any anist command as usual:
   ```bash
   cd ~/your-project
   anist diff -n 2 -m "Update feature"
   ```

## Development

### Setting Up for Development

1. Clone the repo and install in development mode:
   ```bash
   git clone https://github.com/gaetanorispoli/anist.git
   cd ~/repos/anist
   uv pip install -e .
   ```

2. Make changes to the code
3. Run `anist` to test your changes (the installed command will use your modified code)
4. To quickly reinstall after making structural changes:
   ```bash
   uv pip uninstall anist && uv pip install -e .
   ```

### Project Structure

- `src/`
  - `__init__.py` - Package initialization
  - `cli.py` - Command-line interface using Typer
  - `commit.py` - Commit editing functionality
  - `diff.py` - Diff management functionality
  - `utils.py` - Utility functions

### Customizing the Base Branch

By default, anist uses "master" as the base branch. If your repository uses a different base branch (e.g., "main"), you'll need to modify the code in `src/utils.py` to change references from "master" to your base branch name.

---

## Contributors

- [Gaetano Rispoli](https://github.com/risperss)

---

With Anist, managing complex stacked diffs in Phabricator becomes significantly more streamlined, allowing developers to focus on writing code rather than managing complex version control operations.
