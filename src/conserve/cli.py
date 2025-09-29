"""CLI interface for Conserve."""

import traceback
from pathlib import Path

import tyro

from .discovery import discover_all_tasks


def list_tasks(root: Path | None = None) -> None:
    """List all discovered conserve tasks.

    Args:
        root: Root directory to search (default: current directory)
    """
    root = root or Path.cwd()
    print(f"Discovering tasks in: {root}\n")

    tasks = discover_all_tasks(root)
    if not tasks:
        print("No conserve tasks found.")
        print("\nExpected locations:")
        print("  - .conserve/conserve_*.py or .conserve/*_conserve.py")
        print("  - .conserve.py (single file)")
        print("\nFunction naming: conserve_* (no parameters)")
        return

    print(f"Found {len(tasks)} task(s):\n")
    for task_id, _ in tasks:
        print(f"  {task_id}")


def run(
    tasks: list[str] | None = None,
    root: Path | None = None,
    dry_run: bool = False,
) -> None:
    """Run conserve tasks.

    Args:
        tasks: Specific tasks to run (format: "module:function"). If None, run all.
        root: Root directory to search (default: current directory)
        dry_run: Preview what would be run without executing
    """
    root = root or Path.cwd()

    all_tasks = discover_all_tasks(root)
    if not all_tasks:
        print("No conserve tasks found.")
        return

    # Filter tasks if specific ones requested
    if tasks:
        tasks_to_run = []
        for task_pattern in tasks:
            # Support partial matching (just function name)
            matches = [
                (tid, func) for tid, func in all_tasks if tid == task_pattern or tid.endswith(f":{task_pattern}")
            ]
            if not matches:
                print(f"Warning: No task matching '{task_pattern}'")
            tasks_to_run.extend(matches)
    else:
        tasks_to_run = all_tasks

    if not tasks_to_run:
        print("No tasks to run.")
        return

    # Execute tasks
    print(f"{'[DRY RUN] ' if dry_run else ''}Running {len(tasks_to_run)} task(s):\n")

    for task_id, func in tasks_to_run:
        print(f"  → {task_id}")
        if not dry_run:
            try:
                func()
                print("    ✓ Success")
            except Exception as e:
                print(f"    ✗ Failed: {e}")
                traceback.print_exc(limit=3)
        else:
            print("    (skipped - dry run)")


def info(task: str, root: Path | None = None) -> None:
    """Show information about a specific task.

    Args:
        task: Task identifier (format: "module:function" or just "function")
        root: Root directory to search (default: current directory)
    """
    root = root or Path.cwd()

    all_tasks = discover_all_tasks(root)

    # Find matching task
    matches = [(tid, func) for tid, func in all_tasks if tid == task or tid.endswith(f":{task}")]

    if not matches:
        print(f"Task not found: {task}")
        return

    for task_id, func in matches:
        print(f"Task: {task_id}")
        print(f"Module: {task_id.split(':')[0]}")
        print(f"Function: {func.__name__}")

        if func.__doc__:
            print(f"\nDocstring:\n{func.__doc__}")

        # Show source location
        import inspect

        source_file = inspect.getfile(func)
        source_lines, line_num = inspect.getsourcelines(func)
        print(f"\nSource: {source_file}:{line_num}")
        print("".join(source_lines[:10]))  # Show first 10 lines
        if len(source_lines) > 10:
            print(f"... ({len(source_lines) - 10} more lines)")


def main() -> None:
    """Conserve - Configuration fragment synchronizer."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: conserve <command> [options]")
        print("\nCommands:")
        print("  list              List all discovered conserve tasks")
        print("  run               Run conserve tasks")
        print("  info <task>       Show information about a task")
        sys.exit(1)

    command = sys.argv[1]
    commands = {"list": list_tasks, "run": run, "info": info}

    if command in commands:
        tyro.cli(commands[command], args=sys.argv[2:])
    else:
        print(f"Unknown command: {command}")
        print("Use 'conserve --help' for usage information")
        sys.exit(1)


if __name__ == "__main__":
    main()
