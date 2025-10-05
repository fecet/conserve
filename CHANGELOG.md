# Changelog

All notable changes to this project will be documented in this file.
The format is based on Keep a Changelog and this project adheres to Semantic Versioning.

## [0.1.0] - 2025-10-05

### Added
- CLI with `list` / `info` / `apply` (supports `--tasks`, `--yes`, `--dry-run`)
- Plan mode for previewing and batch applying changes with unified diff
- Config handles: `TOMLHandle` / `YAMLHandle` / `JSONHandle`
- Format preservation (TOML via tomlkit, YAML via ruamel.yaml)
- Deep merge utility `merge_deep` (dict recursive; list/scalar replace)
- `TextHandle` with `present`/`absent` line management
- Minimal Package module:
  - `Package(...).latest()` and `info()`
  - Registry metadata via deps.dev provider (pypi/npm/cargo/maven/rubygems/nuget)
  - GitHub releases provider for latest/tag metadata
  - `to_pypi()` / `to_conda()` mapping helpers
- E2E tests covering task discovery, merge strategy, format preservation, CLI flows

### Notes
- Package module is intentionally minimal at this version:
  - Not yet implementing `commit()` / `date()` or advanced version strategies
  - Network access required for providers; consider timeouts/caching in CI

