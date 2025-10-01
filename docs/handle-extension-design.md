# Conserve Handle 系统扩展设计

## 概述

本设计扩展现有的 Handle 系统，为不同类型的文件提供专门的处理能力，并添加 Plan Mode 功能用于预览变更。

## 设计原则

1. **幂等性保证**：所有 Handle 操作必须是幂等的，重复执行产生相同结果
2. **组件复用**：充分利用已有的 File 抽象，避免重复造轮子
3. **简化交互**：Handle 只需提供目标路径和内容给 Plan，由 Plan 管理内存文件
4. **明确的 API**：不提供自动类型检测，用户必须明确选择 Handle 类型
5. **预览与安全**：Plan Mode 提供变更预览和批量提交能力
6. **单线程优化**：针对 CLI 单线程执行模型优化，利用 Python 字典操作的原子性
7. **约定优于配置**：通过明确的使用约定（任务独立、单线程执行）保证系统安全性

## Handle 类型架构

### 1. BaseHandle - 集成 Plan Mode 的基类

```python
class BaseHandle:
    """所有 Handle 的基类，简化的 Plan 集成"""

    def load(self) -> Self:
        """从文件加载内容（幂等）
        - 加载并解析文件内容
        - 文件不存在时初始化为空文档
        """

    def save(self, path: str | Path | None = None, *, stage: bool | None = None) -> None:
        """保存内容到文件

        Args:
            path: 可选的目标路径
            stage: 是否暂存到 Plan（默认：未指定 path 时为 True，指定 path 时为 False）

        行为：
        - save(): 暂存到 plan（stage 默认为 True）
        - save(stage=False): 直接写入原文件
        - save(path="new.yaml"): 直接写入新文件（stage 默认为 False）
        - save(path="new.yaml", stage=True): 暂存写入新文件的操作
        """
        # 自动推断 stage 默认值
        if stage is None:
            stage = (path is None)

        # 决定目标路径
        target_path = path or self.path

        if stage:
            # 暂存到 plan
            from conserve.plan import plan
            plan.stage(Path(target_path), self._get_serialized_content())
        else:
            # 直接写入文件
            File(str(target_path)).write(self._get_serialized_content())

    def _get_serialized_content(self) -> str:
        """子类实现：返回序列化后的内容"""
```

### 2. ConfigHandle - 结构化配置文件（YAML/JSON/TOML）

```python
class ConfigHandle(BaseHandle):
    """结构化配置文件的基类"""

    def read(self) -> dict:
        """返回当前文档内容"""

    def merge(self, patch: dict, strategy: str = "deep") -> Self:
        """合并配置（幂等）
        - deep: 递归合并
        - shallow: 第一层合并
        - override: 完全替换
        """

    def delete(self, *paths: str) -> Self:
        """删除指定路径的键（幂等）
        - 支持点分隔路径如 "server.port"
        - 路径不存在时静默成功
        """

class YAMLHandle(ConfigHandle):
    """YAML 文件处理（使用 ruamel.yaml 保留格式）"""

class TOMLHandle(ConfigHandle):
    """TOML 文件处理（使用 tomlkit 保留格式）"""

class JSONHandle(ConfigHandle):
    """JSON 文件处理（标准库 json）"""
```

### 3. TextHandle - 简单文本文件行管理

```python
class TextHandle(BaseHandle):
    """文本文件的行管理"""

    def present(self, line: str) -> Self:
        """确保行存在（幂等）"""

    def absent(self, line: str) -> Self:
        """确保行不存在（幂等）"""
```

### 4. ASTHandle - 语法树文件处理

```python
class ASTHandle(BaseHandle):
    """语法树文件处理（未来扩展）"""

    def transform(self, node_path: str, transformer: callable) -> Self:
        """转换指定的语法树节点（幂等）"""

    def rewrite(self, content: str) -> Self:
        """完全重写内容（幂等）"""
```

### 5. Plan 模块 - 简化的变更管理

```python
from pathlib import Path
from conserve.utils import File
import difflib
from uuid import uuid4

class Plan:
    """简化的变更计划管理器 - Handle 只需提供路径和内容"""

    def __init__(self):
        # 真实路径 -> 内存文件的映射
        self._staging_map: dict[Path, File] = {}
        # 记录原始内容用于 diff
        self._original_contents: dict[Path, str | None] = {}

    def stage(self, real_path: Path, content: str) -> None:
        """Handle 调用此方法暂存内容
        - Handle 只需提供：目标路径 + 序列化后的内容
        - Plan 负责管理内存文件和映射关系
        """
        # 记录原始内容（首次暂存时）
        if real_path not in self._original_contents:
            real_file = File(str(real_path))
            self._original_contents[real_path] = (
                real_file.read() if real_file.exists() else None
            )

        # 创建内存文件并暂存内容
        memory_path = f"memory://staging/{uuid4()}/{real_path.name}"
        memory_file = File(memory_path)
        memory_file.write(content)
        self._staging_map[real_path] = memory_file

    def get_diff_summary(self) -> str:
        """生成所有变更的 diff 摘要"""
        diffs = []
        for real_path, memory_file in self._staging_map.items():
            original = self._original_contents.get(real_path, "")
            modified = memory_file.read()
            if original != modified:
                diff = difflib.unified_diff(
                    (original or "").splitlines(keepends=True),
                    modified.splitlines(keepends=True),
                    fromfile=str(real_path),
                    tofile=str(real_path)
                )
                diffs.append("".join(diff))
        return "\n".join(diffs)

    def preview(self) -> dict[Path, str]:
        """预览将要写入的内容"""
        return {
            real_path: memory_file.read()
            for real_path, memory_file in self._staging_map.items()
        }

    def commit(self) -> None:
        """批量提交所有暂存的变更"""
        # 直接写入，利用 File 的抽象
        for real_path, memory_file in self._staging_map.items():
            File(str(real_path)).write(memory_file.read())
        self._staging_map.clear()
        self._original_contents.clear()

    def rollback(self) -> None:
        """清空暂存的变更"""
        self._staging_map.clear()
        self._original_contents.clear()

    def clear(self) -> None:
        """清空所有状态（用于任务间隔离）"""
        self._staging_map.clear()
        self._original_contents.clear()

# 全局单例 Plan 实例
# 在顺序执行和遵守使用约定的前提下是安全的
plan = Plan()
```

## API 组织结构

```python
# conserve/core.py - 核心 Handle 实现
from .core import YAMLHandle, TOMLHandle, JSONHandle, BaseHandle

# conserve/plan.py - 简化的变更计划管理
from .plan import plan  # 直接导出单例实例

# conserve/text.py - 文本文件处理（未来扩展）
from .text import TextHandle

# conserve/ast.py - AST 处理（未来扩展）
from .ast import ASTHandle

__all__ = [
    'YAMLHandle', 'TOMLHandle', 'JSONHandle',
    'TextHandle', 'ASTHandle', 'BaseHandle',
    'plan'  # 导出单例实例
]
```

## 使用示例

### CLI 命令

```bash
# 默认：预览变更后确认应用
conserve apply

# 自动确认，跳过交互
conserve apply --yes

# 仅预览，不应用
conserve apply --dry-run

# 运行特定任务
conserve apply --tasks update_config
```

### 编写任务
```python
# .conserve/tasks.py
from conserve.core import YAMLHandle, TOMLHandle, JSONHandle

def conserve_update_configs():
    """更新项目配置文件"""
    # 默认暂存到 Plan
    YAMLHandle("config.yaml").load() \
        .merge({"server": {"port": 8080}}) \
        .save()  # 默认 stage=True

    TOMLHandle("pyproject.toml").load() \
        .merge({"tool": {"myapp": {"version": "2.0"}}}) \
        .save()  # 默认 stage=True

    JSONHandle("package.json").load() \
        .merge({"version": "2.0.0"}) \
        .save()  # 默认 stage=True

    # 如果需要直接写入（跳过 Plan）
    # .save(stage=False)

    # 如果需要导出到其他文件
    # .save("backup.yaml")  # 默认 stage=False
```

### 执行流程示例
```
$ conserve apply

Running 1 task(s)...
  → conserve:conserve_update_configs

============================================================
CHANGES TO BE APPLIED:
============================================================

--- config.yaml
@@ -3,7 +3,7 @@
 server:
   host: localhost
-  port: 8080
+  port: 9000
   workers: 4
-old_setting: deprecated

--- pyproject.toml
  (structural changes detected)

--- package.json
@@ -1,5 +1,5 @@
 {
   "name": "myapp",
-  "version": "1.0.0",
+  "version": "2.0.0",
   "dependencies": {

Apply these changes? [y/N]: y

✓ Successfully applied changes to 3 file(s)
```

## 实现细节

### CLI 层处理
```python
def apply(tasks, root, yes, dry_run):
    """Apply 命令：启用 Plan Mode 的任务执行

    执行流程：
    1. 运行任务 - Handle 自动使用全局 plan 单例暂存变更
    2. 显示 diff 预览
    3. 处理用户确认（--yes 跳过，--dry-run 退出）
    4. 批量提交或回滚
    """
    from conserve.plan import plan

    # 确保开始时状态干净
    plan.clear()

    # 运行任务
    run_tasks(tasks)

    # 显示预览
    if plan._staging_map:
        print(plan.get_diff_summary())

        # 用户确认
        if not dry_run:
            if yes or confirm("Apply changes?"):
                plan.commit()
            else:
                plan.rollback()
```

### 关键设计

1. **简化的交互模型**：Handle 只需调用 `plan.stage(path, content)`，无需了解内存文件细节
   - save() 方法提供直观的 stage 参数，默认行为符合预期
2. **组件复用**：充分利用现有的 File 类处理本地/远程文件和内存文件系统
3. **并发安全**：
   - CLI 是单线程执行模型，任务顺序运行
   - Python 字典的单个操作（赋值、读取）是原子的
4. **清晰的生命周期**：Plan 在 apply 命令执行期间存在，结束后清理
5. **单一入口**：所有操作通过 `conserve apply` 命令执行

## 并发安全性分析

### 设计理念

Conserve 采用**约定优于配置**的设计理念，通过明确的使用约定保证并发安全：

1. **任务独立性**：不同任务不应修改相同文件
2. **单线程执行**：任务内部不应使用线程、异步等并发机制
3. **框架控制并发**：未来的并发优化由框架层面统一管理，而非用户任务

### 使用约定

#### 必须遵守的约定
- ❌ **禁止**：在任务中创建线程或使用 `concurrent.futures`
- ❌ **禁止**：在任务中使用 `asyncio` 或其他异步框架
- ❌ **禁止**：多个任务修改同一个文件
- ✅ **推荐**：每个任务独立管理自己的配置文件
- ✅ **推荐**：保持任务的幂等性

#### 错误示例
```python
# ❌ 错误：任务中使用线程
def conserve_bad_concurrent():
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor() as executor:
        executor.submit(lambda: YAMLHandle("a.yaml").save())
        executor.submit(lambda: YAMLHandle("b.yaml").save())

# ❌ 错误：多任务修改同一文件
def conserve_task_1():
    YAMLHandle("config.yaml").merge({"a": 1}).save()

def conserve_task_2():
    YAMLHandle("config.yaml").merge({"b": 2}).save()  # 冲突！
```

#### 正确示例
```python
# ✅ 正确：每个任务管理不同文件
def conserve_update_backend():
    YAMLHandle("backend.yaml").merge({"port": 8080}).save()

def conserve_update_frontend():
    JSONHandle("frontend.json").merge({"api": "v2"}).save()
```

### 单例 Plan 的安全性保证

在当前的使用约定下，全局单例 Plan 是**并发安全**的：

```python
# CLI 顺序执行任务
for task_id, func in tasks_to_run:
    func()  # 顺序执行，无并发竞争
```

**安全性依赖于**：
1. CLI 层面的顺序执行
2. Python GIL 对字典操作的原子性保护
3. 用户遵守单线程任务的约定
