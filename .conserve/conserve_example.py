"""Example conserve configurations."""

import conserve
from pathlib import Path


def conserve_hello():
    """Simple hello world example."""
    print("Hello from Conserve!")
    print("This is an example task that runs automatically.")


def conserve_demo_merge():
    """Demonstrate merge functionality."""
    # Create demo files
    base_config = Path("demo_base.toml")
    local_config = Path("demo_local.toml")

    # Create base config if not exists
    if not base_config.exists():
        conserve.toml(base_config).replace(
            {
                "app": {
                    "name": "DemoApp",
                    "version": "1.0.0",
                    "debug": False,
                },
                "server": {
                    "host": "0.0.0.0",
                    "port": 8080,
                    "workers": 4,
                },
            }
        ).save()
        print(f"Created {base_config}")

    # Create local overrides if not exists
    if not local_config.exists():
        conserve.toml(local_config).replace(
            {
                "app": {
                    "debug": True,  # Enable debug in local
                },
                "server": {
                    "host": "localhost",  # Use localhost
                    "port": 3000,  # Different port
                },
            }
        ).save()
        print(f"Created {local_config}")

    # Merge configs
    base = conserve.toml(base_config).load().read()
    local = conserve.toml(local_config).load().read()
    merged = conserve.merge_deep(base, local)

    # Save merged result
    runtime_config = Path("demo_runtime.toml")
    conserve.toml(runtime_config).replace(merged).save()

    print(f"\nMerged configuration saved to {runtime_config}")
    print("Merged config:")
    for key, value in merged.items():
        print(f"  {key}: {value}")


def conserve_format_conversion():
    """Convert between different formats."""
    # Create a sample TOML file
    toml_file = Path("sample.toml")
    if not toml_file.exists():
        conserve.toml(toml_file).replace(
            {
                "project": {
                    "name": "conserve",
                    "description": "Configuration synchronizer",
                    "tags": ["config", "sync", "format-preserving"],
                }
            }
        ).save()
        print(f"Created {toml_file}")

    # Convert to YAML
    data = conserve.toml(toml_file).load().read()
    yaml_file = Path("sample.yaml")
    conserve.yaml(yaml_file).replace(data).save()
    print(f"Converted to {yaml_file}")

    # Convert to JSON
    json_file = Path("sample.json")
    conserve.json(json_file).replace(data).save()
    print(f"Converted to {json_file}")

    print("\nAll formats created successfully!")


def conserve_cleanup():
    """Clean up demo files."""
    demo_files = [
        "demo_base.toml",
        "demo_local.toml",
        "demo_runtime.toml",
        "sample.toml",
        "sample.yaml",
        "sample.json",
    ]

    for file in demo_files:
        path = Path(file)
        if path.exists():
            path.unlink()
            print(f"Removed {file}")

    print("\nCleanup complete!")
