# Conserve

可保留格式的“配置片段同步器”。本项目通过最小而明确的 API 将一个或多个来源文档整合为目标文件，并在写回时尽可能保留原有排版与注释。

本文中的 MUST/SHOULD/MAY 术语遵循 RFC 2119/8174。

## 愿景与目标

- 成为可“保留格式与注释”的配置片段同步器（configuration fragment synchronizer）。
- 以单一事实源驱动多项目/多文件的一致性，减少复制和漂移。
- 在不破坏文件审美与结构的前提下进行可预测的更新（可预览、可回滚由 CLI 的干运行等能力逐步增强）。

## 当前能力（与实现对齐）

- 格式保留：
  - TOML 通过 `tomlkit`，保留注释/结构；
  - YAML 通过 `ruamel.yaml`，保留引号与注释；
  - JSON 稳定缩进（不含注释）。
- 深度合并：字典递归合并；列表与标量整体替换（可预测性优先）。
- 句柄 API：`TOMLHandle | YAMLHandle | JSONHandle | AutoHandle`；链式 `load().read()/replace()/merge().save()`。
- 自动发现（pytest 风格）：`.conserve/` 下的 `conserve_*.py` / `*_conserve.py` 与根级 `.conserve.py`；函数 `conserve_*`（`conf_*` 兼容但不推荐）；`_` 前缀视为私有。
- CLI：`list | run [--tasks] [--dry-run] | info <task>`；支持按函数名或 `模块:函数` 过滤。
- Python 3.12+；扩展名驱动的 `AutoHandle`（`.toml/.yaml/.yml/.json`）。

## 快速开始

安装（任选其一）：

```bash
# pip
pip install conserve

# Pixi（推荐用于本仓库）
pixi install
```

列出/运行任务（Pixi 环境）：

```bash
# 列表
pixi run python -m conserve.cli list

# 运行全部或按名过滤（支持函数名或 模块:函数）
pixi run python -m conserve.cli run
pixi run python -m conserve.cli run --tasks conserve_sync_local
pixi run python -m conserve.cli run --tasks .conserve.conserve_sync:conserve_sync_local

# 干运行（不执行，仅展示将运行的任务）
pixi run python -m conserve.cli run --dry-run

# 查看任务信息
pixi run python -m conserve.cli info conserve_sync_local
```

也可使用安装后的入口：

```bash
conserve list
conserve run --tasks conserve_sync_local
conserve info conserve_sync_local
```

## API 与语义

本版本以“句柄”作为稳定接口（未提供 `toml()/yaml()/json()` 顶层函数）。

- 句柄类型：
  - `TOMLHandle(path)`、`YAMLHandle(path)`、`JSONHandle(path)`、`AutoHandle(path)`
- 常用方法：
  - `load() -> self`：从磁盘加载；
  - `read() -> dict`：返回内存文档；
  - `replace(doc) -> self`：替换内存文档；
  - `merge(patch) -> self`：按“字典递归、列表/标量整体替换”策略合并；
  - `save(path: str | Path | None = None) -> None`：写回（默认写回原路径）。
- 辅助函数：
  - `merge_deep(*docs) -> dict`：在内存中先合并多个文档后再写入。

实现细节提示（供预期对齐）：

- 合并基于 `deepmerge`，并对 `tomlkit`/`ruamel.yaml` 对象提供格式保留分支；TOML 中较长列表在合并时会尽量保持多行风格。
- `AutoHandle` 目前仅基于扩展名判定格式。

## 使用示例

合并两个 TOML 并生成运行时配置：

```python
import conserve

base = conserve.TOMLHandle("config.toml").load().read()
local = conserve.TOMLHandle("config.local.toml").load().read()

merged = conserve.merge_deep(base, local)
conserve.TOMLHandle("config.runtime.toml").replace(merged).save()
```

跨格式构建清单（YAML/JSON 并存）：

```python
# .conserve.py
import conserve
import json

def conserve_build_manifest():
    """Build deployment manifest from multiple configs."""
    app = conserve.TOMLHandle("app.toml").load().read()
    deploy = conserve.YAMLHandle("deploy.yaml").load().read()
    features = conserve.JSONHandle("features.json").load().read()

    manifest = {
        "application": app["app"],
        "deployment": deploy["deploy"],
        "features": features["features"],
    }

    manifest["deployment"]["image"] = f"{app['app']['name'].lower()}:{app['app']['version']}"

    conserve.YAMLHandle("manifest.yaml").replace(manifest).save()
    conserve.JSONHandle("manifest.json").replace(manifest).save()
```

## 任务发现（pytest 风格）

- 目录：项目根的 `.conserve/`；或根级单文件 `.conserve.py`。
- 文件：`conserve_*.py` 与 `*_conserve.py`；以下划线开头的文件视为私有。
- 别名：兼容 `conf_*.py` 与 `*_conf.py`，与 conserve 同名冲突时优先 conserve；建议统一使用 `conserve_*` 提升一致性。
- 函数：无参的 `conserve_*`（`_` 前缀私有，忽略）。
- 标识：展示名为函数名；完整名为 `模块:函数`（相对路径去后缀，`/` → `.`）。
- 顺序：按（模块相对路径，函数名）稳定排序。

## 合并与格式策略

- 合并语义（MUST）：
  - 字典递归合并；
  - 列表整体替换；
  - 标量整体替换；
  - 类型冲突时整体替换。
- 格式保留（SHOULD）：
  - TOML 使用 `tomlkit`；YAML 使用 `ruamel.yaml`（保留引号、尽量不换行）。
  - JSON 采用稳定缩进输出（无注释）。
- 写入流程（MUST）：
  - 先在内存 `replace()` 或 `merge()`，再 `save()`；`save()` 不接受数据参数，仅负责落盘。

## 项目结构

- 源码：`src/conserve`（`core.py` 核心 API；`discovery.py` 自动发现；`cli.py` 命令入口）。
- 测试：`tests/`（端到端见 `tests/test_e2e.py`）。
- 规范草案：`spec/spec.md`（若与实现冲突，以本 README 描述的“当前能力”与代码为准）。

## 开发与测试

- 环境与脚本 MUST 使用 Pixi：
  - 列表任务：`pixi run python -m conserve.cli list`
  - 运行任务：`pixi run python -m conserve.cli run [--tasks <name>] [--dry-run]`
  - 任务信息：`pixi run python -m conserve.cli info <task>`
  - 运行测试：`pixi run pytest -q`
- 可选：`pip install -e .` 后可直接使用入口命令 `conserve`。

## 兼容性与限制

- 仅支持结构化文档：TOML/YAML/JSON；`AutoHandle` 目前通过扩展名判定。
- Python 3.12+。
- 不包含语法树级别的片段替换；备份/差异摘要/更细粒度预览等为后续增强方向。

## 可选增强（Roadmap）

- 备份策略（写入前 `.bak` 或版本化）；
- 变更预览与选择性执行（更细粒度的 diff 与过滤）；
- 语法树级片段替换（ast-grep 绑定等）；
- 发现规则可配置与更多格式支持。
- 使用libmagic来识别文件格式，而不是仅依赖扩展名 


