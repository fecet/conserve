#!/usr/bin/env python


import conserve
from pathlib import Path
from packaging.requirements import Requirement
from datamodel_code_generator import InputFileType, DataModelType, PythonVersion, generate
import json


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

    # Report results
    print("✓ Synced dependencies from pyproject.toml to pixi.toml")
    print(f"  Total PyPI dependencies: {len(pypi_deps)}")
    print(f"  → Conda dependencies: {len(conda_deps)}")
    print(f"  → PyPI-only dependencies: {len(pypi_only_deps)}")


def conserve_generate_models() -> None:
    """Generate Pixi models via truth.schemastore and datamodel-code-generator (Python API)."""

    # Get content from schemastore
    content = conserve.truth.schemastore.query("pixi.toml")

    schema_file = conserve.File()
    schema_file.write_text(json.dumps(content, indent=2))

    generate(
        input_=schema_file.path,
        input_file_type=InputFileType.JsonSchema,
        output=Path("src/conserve/model") / "pixi.py",
        output_model_type=DataModelType.PydanticV2BaseModel,
        target_python_version=PythonVersion.PY_312,
        use_union_operator=True,  # Use | instead of Union
        collapse_root_models=False,  # Keep structure for complex schemas
        use_default_kwarg=True,  # Use default= instead of default_factory=
    )
