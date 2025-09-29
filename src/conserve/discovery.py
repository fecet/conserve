"""Auto-discovery mechanism (pytest-style)."""

import importlib.util
import inspect
from pathlib import Path
from typing import Callable


def discover_config_files(root_dir: Path | None = None) -> list[Path]:
    """Discover configuration files following naming conventions.

    Search order:
    1. .conserve/ directory with conserve_*.py or *_conserve.py files
    2. Single .conserve.py file in root
    3. Also support conf_*.py and *_conf.py as aliases
    """
    root_dir = Path(root_dir or Path.cwd())

    config_files = []

    # Check for .conserve directory
    conserve_dir = root_dir / ".conserve"
    if conserve_dir.is_dir():
        patterns = ["conserve_*.py", "*_conserve.py", "conf_*.py", "*_conf.py"]
        for pattern in patterns:
            for file_path in conserve_dir.glob(pattern):
                # Skip private files and avoid duplicates
                if not file_path.name.startswith("_") and file_path not in config_files:
                    config_files.append(file_path)

    # Check for single .conserve.py file
    single_file = root_dir / ".conserve.py"
    if single_file.exists() and not conserve_dir.is_dir():
        config_files.append(single_file)

    return sorted(config_files, key=lambda p: (p.parent.relative_to(root_dir), p.name))


def discover_functions(module_path: Path) -> list[tuple[str, Callable]]:
    """Discover conserve functions in a module.

    Returns list of (function_name, function) tuples.
    Functions must:
    - Have no required parameters
    - Start with 'conserve_' or 'conf_' (conserve preferred)
    - Not start with underscore (private)
    """
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if not (spec and spec.loader):
        return []

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    functions = []
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        # Skip private or non-matching names
        if name.startswith("_") or not (name.startswith("conserve_") or name.startswith("conf_")):
            continue

        # Check if callable without args
        sig = inspect.signature(obj)
        if any(
            p.default is inspect.Parameter.empty
            and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            for p in sig.parameters.values()
        ):
            continue

        functions.append((name, obj))

    return sorted(functions, key=lambda x: x[0])


def discover_all_tasks(root_dir: Path | None = None) -> list[tuple[str, Callable]]:
    """Discover all conserve tasks in the project.

    Returns list of (task_id, function) tuples where task_id is "module:function".
    """
    root_dir = root_dir or Path.cwd()
    tasks = []

    for config_file in discover_config_files(root_dir):
        # Create module identifier
        if config_file.name == ".conserve.py":
            module_id = "conserve"
        else:
            module_id = str(config_file.relative_to(root_dir).with_suffix("")).replace("/", ".")

        for func_name, func in discover_functions(config_file):
            tasks.append((f"{module_id}:{func_name}", func))

    return tasks


def run_task(task_func: Callable) -> None:
    """Execute a conserve task function."""
    task_func()
