# Repository Guidelines

> 本文为贡献者与自动代理的简明指南；术语中的 MUST/SHOULD/MAY 采用 RFC 2119/8174 定义。若本文件与实现不一致，MUST 以 `spec/spec.md` 为准（vNext 规范）。

## Project Structure & Module Organization
- 源码：`src/conserve`（`core.py` 为核心 API，`discovery.py` 为自动发现，`cli.py` 为命令入口）。
- 测试：`tests/`（端到端见 `tests/test_e2e.py`）。
- 规范：`spec/spec.md` 描述 API/行为与合并策略；本地任务脚本位于 `.conserve/` 或单文件 `.conserve.py`。
- 发现规则（pytest 风格）：文件 `conserve_*.py` 或 `*_conserve.py`；函数 `conserve_*`（`conf_*` 兼容但不推荐）；`_` 前缀视为私有。

## Build, Test, and Development Commands
- 环境与脚本 MUST 使用 Pixi：
  - 列表任务：`pixi run python -m conserve.cli list`
  - 运行任务：`pixi run python -m conserve.cli run [--tasks <name>] [--dry-run]`
  - 任务信息：`pixi run python -m conserve.cli info <task>`
  - 运行测试：`pixi run pytest -q`
- 开发安装（可选）：`pixi run pip install -e .`（提供 `conserve` 可执行脚本）。

## Architecture & API Essentials
- 结构化句柄：`toml(path) | yaml(path) | json(path) | auto(path)` 返回句柄，支持链式 `load().read()`、`replace(doc)`、`merge(patch)`、`save()`。
- 合并策略：字典递归合并；列表与标量整体替换（可预测性优先）。等价函数 `merge_deep(*docs)` 可在内存中先计算结果。
- 格式保留：TOML 使用 `tomlkit`，YAML 使用 `ruamel.yaml`，JSON 稳定缩进；MUST 不破坏原有注释与引号（在格式支持范围内）。

## Coding Style & Naming Conventions
- Python `>=3.12`，Ruff 行宽 120；使用现代类型注解（PEP 585）、`pathlib` 与 f-string；优先 `dataclass`，复杂结构可用 `msgspec`。
- 仅对关键代码添加英文注释；避免多余抽象，遵循 DCY 原则。
- 代码格式与静态检查：`pixi run pre-commit run -a`（`ruff-format` 与 `ruff --fix`）。

## Testing Guidelines
- 框架：Pytest。测试命名 `tests/test_*.py`。新增特性或修复 MUST 附带测试；回归问题 MUST 先复现。
- 建议在 e2e 用例中覆盖：任务发现、合并策略、格式保留与 `--dry-run` 行为。

## Commit & Pull Request Guidelines
- 提交信息 MUST 遵循 Conventional Commits（例：`feat: implement deep merge semantics`、`fix: preserve yaml quotes`、`docs: align AGENTS with spec`）。
- PR MUST 包含目标、变更要点、测试命令与输出片段、关联 issue；截图/差异摘要（若涉及文件写入）SHOULD 提供。

## Security & Configuration Tips
- `pixi.lock` 为生成产物，MUST 仅由 Pixi 更新（`.gitattributes` 已设 `merge=binary`）。
- 禁止提交机密；运行时配置 MAY 由 `.conserve/` 任务生成。
