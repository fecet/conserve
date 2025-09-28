#!/usr/bin/env python
"""Bootstrap configuration for Conserve project.

This file synchronizes dependencies from pyproject.toml to pixi.toml,
enabling the project to be self-hosted using its own configuration management.
Uses truth.conda for accurate PyPI to Conda package name conversion.
"""

import conserve
from packaging.requirements import Requirement


def conserve_sync_dependencies():
    """Sync dependencies from @pyproject.toml to @pixi.toml using truth.conda mapping."""

    pyproject = conserve.TOMLHandle("pyproject.toml").load().read()

    # Get PyPI dependencies
    pypi_deps = pyproject.get("project", {}).get("dependencies", [])
    if not pypi_deps:
        print("No dependencies found in pyproject.toml")
        return

    # Parse and categorize dependencies
    conda_deps = {}
    pypi_only_deps = {}
    mappings_used = []

    for dep_spec in pypi_deps:
        req = Requirement(dep_spec)
        pkg_name = req.name
        version = str(req.specifier) or "*"

        # Try PyPI to Conda conversion
        conda_name = conserve.truth.conda.to_conda(pkg_name)

        # If no mapping found, assume PyPI and Conda use the same name
        if not conda_name:
            # Most packages use the same name on both PyPI and Conda
            # e.g., ruamel.yaml, numpy, pandas, etc.
            conda_name = pkg_name

        if conda_name:
            if conda_name != pkg_name:
                mappings_used.append(f"{pkg_name} → {conda_name}")
            conda_deps[conda_name] = version
        else:
            pypi_only_deps[pkg_name] = version

    # Remove PyPI packages that are already in Conda (avoid duplicates)
    if conda_deps and pypi_only_deps:
        conda_pypi_names = {conserve.truth.conda.to_pypi(c) for c in conda_deps if conserve.truth.conda.to_pypi(c)}
        pypi_only_deps = {k: v for k, v in pypi_only_deps.items() if k not in conda_pypi_names}

    # Build and apply updates - merge naturally preserves existing values
    updates = {}
    if conda_deps:
        updates["dependencies"] = conda_deps
    if pypi_only_deps:
        updates["pypi-dependencies"] = pypi_only_deps

    # Apply - merge preserves existing entries like python, pip, conserve
    conserve.TOMLHandle("pixi.toml").load().merge(updates).save()

    # Report results
    print("✓ Synced dependencies from pyproject.toml to pixi.toml")
    print(f"  Total PyPI dependencies: {len(pypi_deps)}")
    print(f"  → Conda dependencies: {len(conda_deps)}")
    print(f"  → PyPI-only dependencies: {len(pypi_only_deps)}")

    if mappings_used:
        print("\n  Package name mappings used:")
        for mapping in mappings_used:
            print(f"    {mapping}")
