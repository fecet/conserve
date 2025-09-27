# Conserve Registry API 规范（简化版）

本规范力图自洽、可评审、可落地。它不仅给出 API 与流程，也合并了项目愿景，力求读完本文件即可判断该方向是否值得推进并提出改进建议。

本方案坚持“足够有表现力且保持简单”，删除 transformer/adapter 等附加机制；通过“函数内基于顶层函数 API（如 toml()/yaml()/json()/auto()）”的显式调用消除歧义并提升表达力。另统一写入语义：始终在内存中 `replace(data)` 或 `merge(data)`，然后调用 `save()`；`save()` 不接受数据参数。

---

## 与现有实现的关系

本规范用于 Conserve 的重写版（vNext）设计，目标是提供一套自洽、可验证、可扩展的最终接口与行为约束。凡与当前代码实现存在冲突或不一致的地方，均以本规范为准；本文不以“兼容当前实现”为目标，也不对现状进行折中处理。

---

## 项目愿景

Conserve 的愿景是：
- 成为“可保留格式与注释”的配置片段同步器（configuration fragment synchronizer）。
- 以单一事实源（single source of truth）驱动多项目、多文件的配置一致性，减少复制粘贴与配置漂移。
- 在不破坏现有文件审美与结构的前提下，进行可预测、可回滚、可预览的变更。
- 拥抱 Python 的可组合性与类型安全（如 msgspec/dataclass），让配置生成既表达力强又可测试。

要解决的问题：
- 多项目/多语言仓库中工具配置分散、易漂移，人工同步易出错。
- 现成模板/脚手架复制后难以演进；格式化/注释容易被覆盖或丢失。
- 需要可预览/可选择/可回滚的安全工作流（可作为后续可选增强方向）。

不追求的方向（非目标）：
- 不做通用模板引擎或构建系统；
- 不做“智能列表合并”，列表一律整体替换以保持可预测性；
- 不引入多层回调魔法，API 面尽量小。

设计原则：
- 简洁优先：零装饰器自动发现 + 单一合并路径；
- 显式优先：以函数体内的顶层函数 API 明确行为（source/target 仅为概念角色）；
- 安全默认：保留注释与格式、写入前后可对比；
- 可测试：强约束错误语义、确定性合并策略；
- 组合而非扩展点繁殖：通过 Python 代码组织复用与差异化。

---

## 核心目标

- 零装饰器：采用 pytest 风格的“按文件名/函数名自动发现”机制，无需显式注册。
- 显式语义：在函数体内以顶层函数 API 读取与写入（如 `toml()/yaml()/json()/auto()`）；需要合并时使用 `merge_deep(...)` 或句柄的 `merge(...)`；
- API 简洁：用纯 Python 组合表达差异（条件、循环、复用）。
- 当前范围：仅支持结构化文档（`toml`、`yaml`、`json`）；`auto` 仅覆盖这三者。
- 增强方向：语法树（tree）用于片段级替换，未来版本基于 ast-grep 的 Python 绑定提供，当前规范不定义其具体 API。

核心能力一览（便于快速评估）：
- 保持格式与注释（TOML: tomlkit；YAML: ruamel.yaml；JSON：稳定缩进）
- 深度合并（仅字典递归；列表/标量整体替换）
- 类型安全（支持 msgspec/dataclass → 基本类型）
  

---

## API 概览（结构化文档）

为简化与聚焦，本版仅规范结构化文档（toml/yaml/json）的最小 API；语法树另见“可选增强”。

顶层函数（创建句柄）：
- `toml(path)`、`yaml(path)`、`json(path)`、`auto(path)` → 返回结构化句柄。

结构化句柄的行为（链式调用约定）：
- `load()` 装载磁盘内容并返回自身；`read()` 返回当前内存文档；
- `replace(doc)` 用新文档替换内存内容并返回自身；
- `merge(patch)` 以“字典深合并、列表/标量整体替换”的策略合并到内存并返回自身；
- `save(path=None)` 将内存内容写回（默认写回创建时的路径）。

辅助函数：
- `merge_deep(*docs) -> dict` 用于在写入前在内存中计算合并结果（同句柄的合并策略）。


### 命名约定与品牌

- 选择 conserve 作为前/后缀，统一品牌心智，突出“保留/保护”的核心价值（conserve == preserve）。
- 与通用的 sync/conf 相比，conserve 更易检索、冲突概率低、表达更聚焦。
- 对齐 pytest 的“前后缀并行（文件）+ 仅前缀（函数）”模式，简单一致。

### 发现与命名（pytest 风格）

- 目录：默认在项目根的 `.conserve/` 目录中发现配置文件；也支持根级单文件 `.conserve.py`。
- 文件（主规则）：匹配 `conserve_*.py` 或 `*_conserve.py`；以下划线开头的文件（如 `_helpers.py`）不参与发现。
- 文件（可选别名）：可兼容 `conf_*.py` 与 `*_conf.py`，但与 conserve 命名冲突时优先采用 conserve 版本。
- 文件扩展名：仅支持标准的 `.py` 文件；不支持 `.rc` 或其他非标准扩展名（保持简单性）。
- 函数（主规则）：匹配无参函数 `conserve_*`；以下划线开头的函数视为私有（不参与发现）。
- 函数（可选别名）：可兼容 `conf_*`，但建议使用 `conserve_*` 以提升一致性与可读性。
- 命名：任务名默认为函数名；用于展示与选择。模块相对路径与函数名组成的"模块:函数"可作为全名标识。
- 顺序：按（模块相对路径，函数名）进行稳定排序；用户可通过文件/函数命名控制顺序。 

---

## 使用模式

### 模式1：基础用法（函数内声明 source/target）

```python
from conserve import toml, yaml, json, merge_deep

def conserve_configs():
    patch = {"tool": {"ruff": toml("base.toml").read().get("linting", {})}}
    toml("pyproject.toml").merge(patch).save()
```

---


### 模式2：共享 Source（辅助函数复用）

```python
from conserve import toml, yaml, json, merge_deep

def load_common() -> dict:
    base = toml("defaults.toml").read()
    over = yaml("overrides.yaml").read()
    return merge_deep(base, over)

def conserve_python_config():
    conf = load_common()
    patch = {"tool": {"ruff": conf.get("linting", {}),
                       "mypy": conf.get("type_checking", {})}}
    toml("pyproject.toml").merge(patch).save()

def conserve_node_config():
    conf = load_common()
    patch = {"scripts": conf.get("scripts", {}),
             "devDependencies": conf.get("js_deps", {})}
    json("package.json").merge(patch).save()
```


## 处理流程

1. 执行注册函数
   - 在函数体内以 `json()/yaml()/toml()/auto()` 读取一个或多个来源（结构化文档）。
   - 以 `merge_deep` 等纯 Python 逻辑计算目标补丁或替换文本。

2. 写入目标
   - 结构化目标：读取目标文件 → `merge(patch)` 或 `replace(doc)` → `save()`（保持格式与注释）。


---

## 合并与格式策略（结构化文档）

- 深度合并（通过 `conserve.merge_deep` 提供给用户按需调用）：仅对字典递归；列表与标量整体替换，不做去重/拼接，以保持可预测性。
- TOML：使用 `tomlkit`，保留注释与结构；
- YAML：使用 `ruamel.yaml`，保留注释与引号；
- JSON：标准缩进与换行（不含注释）。

---

## 可选增强（非核心范围，供后续讨论）

- 备份策略：写入前创建 `.bak` 备份，或提供版本化备份选项；可在全局或单目标级别开启/关闭。
- 变更预览：干运行模式（dry-run），输出将写入的目标列表与关键变更摘要。
- 选择性执行：按函数名或"模块:函数"过滤执行子集，便于调试与分步应用。
- 语法树（增强，当前版本不实现）：采用 ast-grep 的 Python 绑定，提供 selector 驱动的片段级替换与命中诊断；本规范不定义其具体 API，待未来版本补充。
- 发现规则可配置：允许通过配置键覆盖默认文件/函数匹配模式（例如 conserve_files、conserve_functions）。
- 特殊文件支持：如需支持 `.conserve.rc` 或其他非标准扩展名作为元配置，可在未来版本考虑（需权衡复杂度）。
- 更多语言/格式支持可在语法树增强基础上扩展（如 xml/html/java/cpp 等）。
