#!/usr/bin/env python
"""Bootstrap configuration for Conserve project.

This file synchronizes dependencies from pixi.toml to pyproject.toml,
enabling the project to be self-hosted using its own configuration management.
"""

import conserve
from pathlib import Path


def conserve_sync_dependencies():
    """Sync dependencies from @pixi.toml to @pyproject.toml."""

    pixi_path = Path("pixi.toml")
    pyproject_path = Path("pyproject.toml")

    if not pixi_path.exists():
        print("Warning: pixi.toml not found")
        return

    if not pyproject_path.exists():
        print("Warning: pyproject.toml not found")
        return

    pixi = conserve.toml(pixi_path).load().read()
    pyproject = conserve.toml(pyproject_path).load()

    dependencies = []

    # Extract dependencies from pixi.toml
    if "dependencies" in pixi:
        conda_deps = pixi["dependencies"]
        for dep, version in conda_deps.items():
            if dep == "python":
                continue
            if dep in ["pip", "hatchling", "pytest"]:
                continue
            if dep in ["tyro", "tomlkit", "msgspec"]:
                dependencies.append(dep)

    if "pypi-dependencies" in pixi:
        pypi_deps = pixi["pypi-dependencies"]
        for dep, spec in pypi_deps.items():
            if dep == "conserve":
                continue
            if isinstance(spec, dict) and "path" in spec:
                continue
            if dep == "deepmerge":
                dependencies.append("deepmerge")
            elif isinstance(spec, str):
                if spec == "*":
                    dependencies.append(dep)
                else:
                    dependencies.append(f"{dep}{spec}")

    # Core runtime dependencies
    core_deps = ["tyro", "tomlkit", "ruamel.yaml", "deepmerge"]
    for dep in core_deps:
        if dep not in dependencies:
            dependencies.append(dep)

    # Sort and deduplicate
    dependencies = sorted(set(dependencies))

    # Only update the dependencies field, preserving everything else
    # Let conserve handle format preservation automatically
    pyproject.merge({"project": {"dependencies": dependencies}}).save()

    print("✓ Synced dependencies from pixi.toml to pyproject.toml")
    print(f"  Dependencies: {', '.join(dependencies)}")


# Removed conserve_bootstrap function - it was redundant
# conserve_sync_dependencies is sufficient as the bootstrap task
