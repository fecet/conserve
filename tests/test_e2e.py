"""End-to-end tests for Conserve."""

import json
import subprocess

import tomlkit
from ruamel.yaml import YAML


def test_e2e_config_sync(tmp_path):
    """Test end-to-end configuration synchronization workflow."""

    # Setup: Create project structure with configs
    project = tmp_path / "project"
    project.mkdir()

    # Create base config files
    base_config = project / "config.toml"
    base_config.write_text("""
[server]
host = "localhost"
port = 8080

[database]
url = "postgres://localhost/mydb"
pool_size = 10
""")

    local_config = project / "config.local.toml"
    local_config.write_text("""
[server]
port = 3000  # Development port

[database]
url = "postgres://localhost/devdb"
""")

    # Create .conserve directory with sync script
    conserve_dir = project / ".conserve"
    conserve_dir.mkdir()

    sync_script = conserve_dir / "conserve_sync.py"
    sync_script.write_text("""
import conserve
from pathlib import Path

def conserve_sync_local():
    \"\"\"Sync local config overrides.\"\"\"
    # Load base and local configs
    base = conserve.TOMLHandle("config.toml").load().read()
    local = conserve.TOMLHandle("config.local.toml").load().read()

    # Merge local overrides into base
    merged = conserve.merge_deep(base, local)

    # Save as runtime config (direct write, not staged)
    conserve.TOMLHandle("config.runtime.toml").replace(merged).save(stage=False)

def conserve_update_ports():
    \"\"\"Update all port configurations.\"\"\"
    # Update ports in all config files
    configs = ["config.toml", "config.local.toml"]

    for config_file in configs:
        path = Path(config_file)
        if path.exists():
            handle = conserve.TOMLHandle(path).load()
            doc = handle.read()

            # Update port if server section exists
            if "server" in doc and "port" in doc["server"]:
                doc["server"]["port"] = doc["server"]["port"] + 10000
                handle.replace(doc).save(stage=False)
""")

    # Run conserve to sync configs
    subprocess.run(
        ["python", "-m", "conserve.cli", "apply", "--yes"],
        cwd=project,
        capture_output=True,
        text=True,
    )

    # Check runtime config was created with merged values
    runtime_config = project / "config.runtime.toml"
    assert runtime_config.exists()

    runtime = tomlkit.loads(runtime_config.read_text())
    assert runtime["server"]["host"] == "localhost"
    assert runtime["server"]["port"] == 3000  # From local override
    assert runtime["database"]["url"] == "postgres://localhost/devdb"  # From local
    assert runtime["database"]["pool_size"] == 10  # From base

    # Check that ports were updated
    base_updated = tomlkit.loads(base_config.read_text())
    assert base_updated["server"]["port"] == 18080  # 8080 + 10000

    local_updated = tomlkit.loads(local_config.read_text())
    assert local_updated["server"]["port"] == 13000  # 3000 + 10000


def test_e2e_multi_format_workflow(tmp_path):
    """Test working with multiple config formats."""

    project = tmp_path / "multi_format"
    project.mkdir()

    # Create configs in different formats
    toml_config = project / "app.toml"
    toml_config.write_text("""
[app]
name = "MyApp"
version = "1.0.0"
""")

    yaml_config = project / "deploy.yaml"
    yaml_config.write_text("""
deploy:
  environment: production
  replicas: 3
  resources:
    cpu: "500m"
    memory: "1Gi"
""")

    json_config = project / "features.json"
    json_config.write_text(json.dumps({"features": {"auth": True, "analytics": False, "beta": True}}, indent=2))

    # Create conserve script to combine all configs
    conserve_script = project / ".conserve.py"
    conserve_script.write_text("""
import conserve
import json

def conserve_build_manifest():
    \"\"\"Build deployment manifest from all configs.\"\"\"

    # Load configs from different formats
    app = conserve.TOMLHandle("app.toml").load().read()
    deploy = conserve.YAMLHandle("deploy.yaml").load().read()
    features = conserve.JSONHandle("features.json").load().read()

    # Build unified manifest
    manifest = {
        "application": app["app"],
        "deployment": deploy["deploy"],
        "features": features["features"]
    }

    # Add computed fields
    manifest["deployment"]["image"] = f"{app['app']['name'].lower()}:{app['app']['version']}"

    # Save as both YAML and JSON (direct write)
    conserve.YAMLHandle("manifest.yaml").replace(manifest).save(stage=False)
    conserve.JSONHandle("manifest.json").replace(manifest).save(stage=False)
""")

    # Run conserve
    subprocess.run(
        ["python", "-m", "conserve.cli", "apply", "--yes"],
        cwd=project,
        capture_output=True,
        text=True,
    )

    # Verify manifest was created correctly
    yaml_manifest = project / "manifest.yaml"
    json_manifest = project / "manifest.json"

    assert yaml_manifest.exists()
    assert json_manifest.exists()

    # Check YAML content
    yaml = YAML()
    yaml_content = yaml.load(yaml_manifest.read_text())

    assert yaml_content["application"]["name"] == "MyApp"
    assert yaml_content["deployment"]["environment"] == "production"
    assert yaml_content["deployment"]["image"] == "myapp:1.0.0"
    assert yaml_content["features"]["auth"] is True

    # Check JSON content matches
    json_content = json.loads(json_manifest.read_text())
    assert json_content == yaml_content


def test_e2e_cli_commands(tmp_path):
    """Test CLI command functionality."""

    project = tmp_path / "cli_test"
    project.mkdir()

    # Create test conserve files
    conserve_dir = project / ".conserve"
    conserve_dir.mkdir()

    task1 = conserve_dir / "conserve_tasks.py"
    task1.write_text("""
from pathlib import Path

def conserve_task_one():
    \"\"\"First test task.\"\"\"
    Path("task1.txt").write_text("Task 1 executed")

def conserve_task_two():
    \"\"\"Second test task.\"\"\"
    Path("task2.txt").write_text("Task 2 executed")

def helper_function():
    \"\"\"This should not be discovered.\"\"\"
    pass
""")

    # Test list command
    result = subprocess.run(
        ["python", "-m", "conserve.cli", "list"],
        cwd=project,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "conserve_task_one" in result.stdout
    assert "conserve_task_two" in result.stdout
    assert "helper_function" not in result.stdout

    # Test apply specific task
    result = subprocess.run(
        ["python", "-m", "conserve.cli", "apply", "--tasks", "conserve_task_one", "--yes"],
        cwd=project,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (project / "task1.txt").exists()
    assert not (project / "task2.txt").exists()

    # Test apply all tasks
    result = subprocess.run(
        ["python", "-m", "conserve.cli", "apply", "--yes"],
        cwd=project,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (project / "task2.txt").exists()

    # Test dry-run
    (project / "task3.txt").unlink(missing_ok=True)

    task2 = conserve_dir / "conserve_dry.py"
    task2.write_text("""
from pathlib import Path

def conserve_dry_task():
    Path("task3.txt").write_text("Should not exist in dry run")
""")

    result = subprocess.run(
        ["python", "-m", "conserve.cli", "apply", "--dry-run"],
        cwd=project,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "[DRY RUN]" in result.stdout or "No changes to apply" in result.stdout
    assert not (project / "task3.txt").exists()


def test_e2e_shared_source_pattern(tmp_path):
    """Test the shared source pattern from spec."""

    project = tmp_path / "shared_source"
    project.mkdir()

    # Create initial configs
    base_toml = project / "base.toml"
    base_toml.write_text("""
[common]
app_name = "SharedApp"
version = "2.0.0"
timeout = 30
""")

    app1_yaml = project / "app1.yaml"
    app1_yaml.write_text("""
service:
  name: service-one
  port: 8001
""")

    app2_yaml = project / "app2.yaml"
    app2_yaml.write_text("""
service:
  name: service-two
  port: 8002
""")

    # Create conserve script implementing shared source pattern
    conserve_script = project / ".conserve.py"
    conserve_script.write_text("""
import conserve

def conserve_sync_common():
    \"\"\"Sync common config to all services.\"\"\"
    # Single source of truth
    source = conserve.TOMLHandle("base.toml")

    # Multiple targets
    targets = [
        conserve.YAMLHandle("app1.yaml"),
        conserve.YAMLHandle("app2.yaml"),
    ]

    # Load source
    common = source.load().read()["common"]

    # Update all targets
    for target in targets:
        doc = target.load().read()
        # Add common config to each service
        doc["common"] = common
        target.replace(doc).save(stage=False)

def conserve_update_versions():
    \"\"\"Update version in all files consistently.\"\"\"
    new_version = "2.1.0"

    # Update base
    base = conserve.TOMLHandle("base.toml").load()
    base_doc = base.read()
    base_doc["common"]["version"] = new_version
    base.replace(base_doc).save(stage=False)

    # Update all app configs if they have version
    for config_file in ["app1.yaml", "app2.yaml"]:
        from pathlib import Path
        if Path(config_file).exists():
            handle = conserve.YAMLHandle(config_file).load()
            doc = handle.read()
            if "common" in doc and "version" in doc["common"]:
                doc["common"]["version"] = new_version
                handle.replace(doc).save(stage=False)
""")

    # Run sync
    result = subprocess.run(
        ["python", "-m", "conserve.cli", "apply", "--tasks", "conserve_sync_common", "--yes"],
        cwd=project,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Verify common config was synced
    yaml = YAML()

    app1 = yaml.load(app1_yaml.read_text())
    assert app1["common"]["app_name"] == "SharedApp"
    assert app1["common"]["version"] == "2.0.0"
    assert app1["service"]["name"] == "service-one"  # Original preserved

    app2 = yaml.load(app2_yaml.read_text())
    assert app2["common"]["app_name"] == "SharedApp"
    assert app2["common"]["version"] == "2.0.0"
    assert app2["service"]["name"] == "service-two"  # Original preserved

    # Run version update
    result = subprocess.run(
        ["python", "-m", "conserve.cli", "apply", "--tasks", "conserve_update_versions", "--yes"],
        cwd=project,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Verify versions updated everywhere
    base = tomlkit.loads(base_toml.read_text())
    assert base["common"]["version"] == "2.1.0"

    app1 = yaml.load(app1_yaml.read_text())
    assert app1["common"]["version"] == "2.1.0"

    app2 = yaml.load(app2_yaml.read_text())
    assert app2["common"]["version"] == "2.1.0"
