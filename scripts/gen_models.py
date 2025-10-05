import json
import tempfile
from pathlib import Path

import schemastore
from datamodel_code_generator import DataModelType, InputFileType, PythonVersion, generate

from conserve.utils import to_valid_filename


def query_schema(name: str) -> dict | None:
    """Query schema by name from schemastore catalog."""
    store = schemastore._Store()
    registry = schemastore.registry()

    # Search by name (case-insensitive, with/without extensions)
    for schema in store.catalog.get("schemas", []):
        schema_name = schema.get("name", "")
        # Try exact match or case-insensitive match
        if schema_name == name or schema_name.lower() == name.lower():
            url = schema.get("url")
            if url:
                try:
                    return registry.get_or_retrieve(url).value.contents  # type: ignore[no-any-return]
                except Exception:
                    return None
    return None


def conserve_generate_models() -> None:
    """Generate Pixi models via schemastore and datamodel-code-generator (Python API)."""

    names = ["pixi.toml", "Claude Code Settings"]

    for name in names:
        content = query_schema(name)

        if not content:
            print(f"Schema for {name} not found, skipping model generation.")
            continue

        # Write schema to temporary file for datamodel-code-generator
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(content, f, indent=2)
            schema_path = f.name

        try:
            # Convert name to valid Python filename
            module_name = to_valid_filename(name)

            generate(
                input_=Path(schema_path),
                input_file_type=InputFileType.JsonSchema,
                output=Path("src/conserve/model") / f"{module_name}.py",
                output_model_type=DataModelType.PydanticV2BaseModel,
                target_python_version=PythonVersion.PY_312,
                use_union_operator=True,  # Use | instead of Union
                collapse_root_models=False,  # Keep structure for complex schemas
                use_default_kwarg=True,  # Use default= instead of default_factory=
            )
        finally:
            # Clean up temp file
            Path(schema_path).unlink(missing_ok=True)
