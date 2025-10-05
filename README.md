# Conserve

面向多格式配置文件（TOML/YAML/JSON）的片段同步与格式保留工具。提供统一的句柄（Handle）API、可预览的 Plan 模式，以及简洁的任务发现与 CLI。

> 依赖与脚本建议通过 Pixi 执行；示例均给出 `pixi run` 形式。

## 特性

- 配置句柄：`TOMLHandle`/`YAMLHandle`/`JSONHandle`，链式 `load().read()`、`merge()`、`replace()`、`save()`
- 合并策略：字典递归；列表与标量整体替换（可预测、可回滚）
- 格式保留：TOML 使用 `tomlkit`，YAML 使用 `ruamel.yaml`（保留引号、不强制换行）
- Plan 模式：先暂存变更，统一 diff 预览后批量提交或回滚
- 任务发现：按 pytest 风格约定发现 `conserve_*` 函数
- CLI：`list`/`info`/`apply`，支持 `--tasks`、`--yes`、`--dry-run`
- 文本句柄：`TextHandle` 提供 `present/absent` 行管理
- Package 模块：基于 PURL 的最小查询（详见“当前能力与边界”）

## 环境要求

- Python >= 3.12
- 推荐使用 Pixi（仓库内含 `pixi.toml`/`pixi.lock`）

## 安装与运行

使用 Pixi 本地开发安装（提供 `conserve` 可执行脚本）：

```bash
pixi run pip install -e .
```

列出与运行任务：

```bash
# 列表任务
pixi run python -m conserve.cli list

# 运行所有任务（预览后确认）
pixi run python -m conserve.cli apply

# 指定任务并自动确认
pixi run python -m conserve.cli apply --tasks <name> --yes

# 仅预览
pixi run python -m conserve.cli apply --dry-run

# 查看任务信息
pixi run python -m conserve.cli info <name>
```

## 快速开始

在项目根目录创建 `.conserve.py` 或 `.conserve/` 下的任务文件，按约定暴露 `conserve_*` 函数（无参）。

```python
# .conserve.py
import conserve

def conserve_sync():
    """Sync config fragments."""
    # Read -> merge -> save (direct write)
    base = conserve.TOMLHandle("config.toml").load().read()
    local = conserve.TOMLHandle("config.local.toml").load().read()
    merged = conserve.merge_deep(base, local)  # deep-merge dicts
    conserve.TOMLHandle("config.runtime.toml").replace(merged).save(stage=False)

def conserve_bump_ports():
    """Update ports in-place."""
    h = conserve.TOMLHandle("config.toml").load()
    doc = h.read()
    if "server" in doc and "port" in doc["server"]:
        doc["server"]["port"] += 10000  # bump
        h.replace(doc).save(stage=False)
```

运行：

```bash
pixi run python -m conserve.cli apply --yes
```

## 合并与格式保留

- 合并（`merge_deep` 与 `ConfigHandle.merge`）：
  - dict：递归合并
  - list/scalar：整体替换
- 格式保留：
  - TOML：保留数组多行、表结构；写回稳定
  - YAML：保留引号与宽度（默认极大，避免自动换行）

## Plan 模式与 CLI

- `save()` 默认暂存到全局 `plan`，集中 diff 预览；`save(stage=False)` 直接写回
- `apply` 流程：执行任务 → 打印 diff → 交互确认或 `--yes` 自动提交
- `--dry-run` 仅打印将执行的任务，不产生文件写入

## Package 模块：当前能力与边界

- 目标：基于 PURL 统一查询包版本与元数据
- 现状（与 docs/package-module-spec.md 对齐说明）：
  - 已实现：`Package(purl_or_short)`、`latest()`、`info()`、`to_pypi()`、`to_conda()`
  - Provider：
    - 注册表类（pypi/npm 等）通过 deps.dev 查询默认/最新版本与元数据
    - GitHub 通过 Releases 获取 `latest` 与指定 `tag` 信息
  - 暂未实现：`commit()`、`date()`、版本选择策略（`latest_tag_semver` 等）
  - 含网络访问；CI/离线环境需考虑超时与缓存

## 测试

```bash
pixi run pytest -q
```

端到端用例覆盖：任务发现、合并策略、格式保留、CLI `--dry-run/--yes` 等。

## 约定与贡献

- 代码风格与工作流：见 `AGENTS.md`
- 提交信息遵循 Conventional Commits

## 许可证与链接

- License: MIT（见 `pyproject.toml`）
- Repository / Issues：见 `pyproject.toml` 对应链接

