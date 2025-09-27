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
    if root_dir is None:
        root_dir = Path.cwd()
    else:
        root_dir = Path(root_dir)

    config_files = []

    # Check for .conserve directory
    conserve_dir = root_dir / ".conserve"
    if conserve_dir.is_dir():
        # Primary patterns: conserve_*.py and *_conserve.py
        patterns = ["conserve_*.py", "*_conserve.py", "conf_*.py", "*_conf.py"]
        for pattern in patterns:
            for file_path in conserve_dir.glob(pattern):
                # Skip files starting with underscore (private)
                if not file_path.name.startswith("_"):
                    # Prefer conserve over conf when both exist
                    base_name = file_path.stem
                    if "conf" in base_name and "conserve" not in base_name:
                        # Check if conserve version exists
                        conserve_version = base_name.replace("conf", "conserve")
                        if (conserve_dir / f"{conserve_version}.py").exists():
                            continue
                    if file_path not in config_files:
                        config_files.append(file_path)

    # Check for single .conserve.py file
    single_file = root_dir / ".conserve.py"
    if single_file.exists() and not conserve_dir.is_dir():
        config_files.append(single_file)

    # Sort by (relative path, filename) for stable order
    config_files.sort(key=lambda p: (p.parent.relative_to(root_dir), p.name))
    return config_files


def discover_functions(module_path: Path) -> list[tuple[str, Callable]]:
    """Discover conserve functions in a module.

    Returns list of (function_name, function) tuples.
    Functions must:
    - Have no required parameters
    - Start with 'conserve_' or 'conf_' (conserve preferred)
    - Not start with underscore (private)
    """
    # Load module dynamically
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        return []

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    functions = []
    for name, obj in inspect.getmembers(module):
        # Skip private functions
        if name.startswith("_"):
            continue

        # Check if it's a function
        if not inspect.isfunction(obj):
            continue

        # Check naming convention
        if not (name.startswith("conserve_") or name.startswith("conf_")):
            continue

        # Check parameters (must be callable without args)
        sig = inspect.signature(obj)
        required_params = [
            p
            for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        if required_params:
            continue

        functions.append((name, obj))

    # Sort by function name for stable order
    functions.sort(key=lambda x: x[0])
    return functions


def discover_all_tasks(root_dir: Path | None = None) -> list[tuple[str, Callable]]:
    """Discover all conserve tasks in the project.

    Returns list of (task_id, function) tuples where task_id is "module:function".
    """
    tasks = []
    config_files = discover_config_files(root_dir)

    for config_file in config_files:
        # Create module identifier (relative path without extension)
        if config_file.name == ".conserve.py":
            module_id = "conserve"
        else:
            relative_path = config_file.relative_to(root_dir or Path.cwd())
            module_id = str(relative_path.with_suffix("")).replace("/", ".")

        functions = discover_functions(config_file)
        for func_name, func in functions:
            task_id = f"{module_id}:{func_name}"
            tasks.append((task_id, func))

    return tasks


def run_task(task_func: Callable) -> None:
    """Execute a conserve task function."""
    task_func()
