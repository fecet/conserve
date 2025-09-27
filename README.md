# Conserve

Configuration fragment synchronizer with format preservation.

Conserve helps you manage and synchronize configuration fragments across multiple files while preserving formatting, comments, and structure.

## Features

- **Format Preservation**: Maintains comments, quotes, and formatting in TOML, YAML, and JSON files
- **Deep Merge**: Intelligent merging of configuration fragments with predictable semantics
- **Bootstrap Support**: Self-hosted configuration management
- **Multi-Format**: Works seamlessly across TOML, YAML, and JSON formats
- **Task Discovery**: Pytest-style auto-discovery of configuration tasks

## Installation

```bash
pip install conserve
```

Or with Pixi:

```bash
pixi install
pixi run conserve list
```

## Usage

### API

```python
import conserve

# Load and merge configurations
base = conserve.toml("config.toml").load().read()
local = conserve.toml("config.local.toml").load().read()
merged = conserve.merge_deep(base, local)

# Save with format preservation
conserve.toml("runtime.toml").replace(merged).save()
```

### CLI

```bash
# List all discovered tasks
conserve list

# Run specific tasks
conserve run --tasks conserve_sync_dependencies

# Dry run to preview changes
conserve run --dry-run
```

### Bootstrap Configuration

Enable self-hosted configuration by creating tasks in the `.conserve/` directory:

```python
# .conserve/conserve_bootstrap.py
import conserve

def conserve_sync_dependencies():
    """Sync dependencies from pixi.toml to pyproject.toml"""
    pixi = conserve.toml("pixi.toml").load().read()
    pyproject = conserve.toml("pyproject.toml").load()

    # Your bootstrap logic here
    dependencies = extract_dependencies(pixi)
    pyproject.merge({"project": {"dependencies": dependencies}}).save()
```

This allows Conserve to manage its own configuration using its own tools.

## License

MIT