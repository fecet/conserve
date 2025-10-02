import conserve
from conserve.utils import to_valid_filename
from pathlib import Path
from datamodel_code_generator import InputFileType, DataModelType, PythonVersion, generate
import json


def conserve_generate_models() -> None:
    """Generate Pixi models via truth.schemastore and datamodel-code-generator (Python API)."""

    names = ["pixi.toml", "Claude Code Settings"]

    contents = conserve.truth.schemastore.query(names)

    for name, content in zip(names, contents):
        schema_file = conserve.File()
        schema_file.write_text(json.dumps(content, indent=2))

        if not content:
            print(f"Schema for {name} not found, skipping model generation.")
            continue

        # Convert name to valid Python filename
        module_name = to_valid_filename(name)

        generate(
            input_=schema_file.path,
            input_file_type=InputFileType.JsonSchema,
            output=Path("src/conserve/model") / f"{module_name}.py",
            output_model_type=DataModelType.PydanticV2BaseModel,
            target_python_version=PythonVersion.PY_312,
            use_union_operator=True,  # Use | instead of Union
            collapse_root_models=False,  # Keep structure for complex schemas
            use_default_kwarg=True,  # Use default= instead of default_factory=
        )
