#!/usr/bin/env python

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

    for dep_spec in pypi_deps:
        req = Requirement(dep_spec)
        pkg_name = req.name
        version = str(req.specifier) or "*"

        # Try PyPI to Conda conversion (now handles normalization internally)
        conda_name = conserve.truth.conda.query_conda(pkg_name)

        if conda_name:
            # Package exists in Conda (with mapped or same name)
            conda_deps[conda_name] = version
        else:
            # Package only exists in PyPI
            pypi_only_deps[pkg_name] = version

    # Apply - merge preserves existing entries like python, pip, conserve
    conserve.TOMLHandle("pixi.toml").load().merge(
        {
            "dependencies": conda_deps,
            "pypi-dependencies": pypi_only_deps,
        }
    ).save()
