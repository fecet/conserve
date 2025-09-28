# Conserve Truth 模块规范（Normative）

> 本文档使用 RFC 2119/8174 术语（MUST/SHOULD/MAY 等）表达规范性要求；若与 `spec/spec.md` 存在冲突，MUST 以 `spec/spec.md` 为准。本文档覆盖 `conserve.truth` 命名空间内所有提供者（provider）的设计与实现约束，适用于新增与维护型改动。

## 1. 目标与范围

- Truth 模块的目标是为 Conserve 任务提供“只读、可预测、可缓存”的外部事实来源（host、git、github、http、docker、path、pypi、conda 等）。
- 提供者 API MUST 以简单的函数为主，必要时 MAY 提供面向高级用例的类封装；所有 API 默认无副作用（读取而非写入）。
- 本规范关注：命名与结构、返回类型、错误模型、缓存策略、配置/安全、测试与稳定性要求；不强制实现顺序与性能指标，但定义最低可用线（MVP）。

## 2. 术语

- “提供者（provider）”：`conserve.truth.<name>` 子模块及其公开 API。
- “调用方（caller）”：Conserve 任务函数（`conserve_*`）或其他内部模块。
- “事实（truth）”：可引用的外部/环境信息（平台、VCS 状态、注册表元数据等），强调确定性与可重现。

## 3. 顶层结构与命名

- 模块路径 MUST 为 `src/conserve/truth/<provider>.py`；在 `src/conserve/truth/__init__.py` 中以子模块形式导出。
- 提供者公开 API MUST 使用蛇形命名（snake_case），参数名与语义 MUST 一致：
  - `ref`（VCS/内容版本标识），`timeout`（秒，浮点数），`retries`（整数），`headers`（HTTP 头），`refresh`（布尔，忽略缓存）。
- 函数名 SHOULD 为名词性或属性式语义（如 `platform()`、`sha()`），避免前缀 `get_`；批量/集合语义使用复数名（如 `tags()`、`versions()`）。

## 4. 返回类型与时区/文本约定

- API 返回值 MUST 采用内置类型（`str|int|float|bool|dict|list|None`）。需要结构化时 SHOULD 使用 `dataclass`（不依赖第三方）。
- 时间戳 MUST 为 ISO8601 UTC（形如 `2025-09-28T16:00:00Z`），文件系统 `mtime()` MAY 返回 `datetime`（UTC、naive 禁止）。
- 文本编码 MUST 以 UTF-8 为默认；HTTP/远程内容若带 `Content-Type`/BOM/显式声明，SHOULD 遵循其编码，否则退回 UTF-8。

## 5. 错误模型

- 定义基类异常 `TruthError`（MUST）。建议子类：
  - `TruthNotAvailable`（运行环境/工具缺失，如未安装 git/docker），
  - `TruthNotFound`（对象不存在：文件、镜像、标签等），
  - `TruthUnauthorized`（鉴权失败/凭据缺失），
  - `TruthRateLimited`（被限流），
  - `TruthTimeout`（超时），
  - `TruthParseError`（响应解析失败）。
- 开发者 MUST 根据情形抛出最贴切的异常；调用方可据此采取降级或重试。返回 `None` 仅用于“确实是空/不存在但非错误”的场景（例如可选的 tag）。

## 6. 缓存与一致性

- 所有提供者默认不缓存（MUST）。凡实现缓存：
  - 提供 `refresh: bool = False` 参数（MUST）。
  - 支持全局或作用域缓存（装饰器或上下文管理器）（SHOULD）。
  - TTL 单位为秒（MUST），默认 TTL MAY 由实现决定；磁盘缓存目录 SHOULD 可由 `CONSERVE_TRUTH_CACHE_DIR` 覆盖。
  - 发生网络错误时不得静默返回过期数据（MUST NOT），除非调用方显式声明可接受（例如 `stale_if_error=True`）。

## 7. 依赖与实现约束

- Python 版本 MUST 为 `>=3.12`；类型注解 MUST 采用现代风格（PEP 585/`| None` 等）。
- 网络访问 SHOULD 首选标准库（`urllib` 等）。若确需第三方，MUST 在评审中给出充分理由，且遵循项目依赖策略（见 `pyproject.toml`）。
- 路径处理 MUST 使用 `pathlib`；字符串格式化 MUST 使用 f-string。
- 避免重复实现（DCY）：跨提供者可复用逻辑 SHOULD 放入 `src/conserve/truth/_utils.py`。

## 8. 提供者规范（Provider Specs）

以下条目描述各提供者的最小稳定面（MVP）。实现可以扩展，但 MUST 保持向后兼容。

### 8.1 host（本机环境）

- `platform() -> str`：返回 `linux|darwin|windows`（MUST）。
- `arch() -> str`：返回 `x86_64|arm64|aarch64|armv7l|...`（MUST）。
- `hostname() -> str`、`user() -> str`、`home() -> str`（MUST）。
- `python() -> str`（如 `3.12.1`），`python_version() -> tuple[int,int,int]`，`venv() -> str|None`（SHOULD）。
- `env(key: str, default: str|None=None) -> str|None`（MUST）。
- `has_command(cmd: str) -> bool`（MUST）。

### 8.2 git（当前工作副本）

- 前置条件：工作目录在 Git 仓库内，否则 MUST 抛出 `TruthNotAvailable`。
- `branch() -> str`、`sha(short: bool=False) -> str`、`tag() -> str|None`、`dirty() -> bool`（MUST）。
- `ahead() -> int`、`behind() -> int`：如无上游分支 MUST 返回 `0` 而非抛错（SHOULD 记录告警）。
- `remote() -> str|None`、`remote_url() -> str|None`（SHOULD）。
- `author() -> str|None`、`email() -> str|None`、`last_commit() -> dict`（`{"sha","message","author","email","timestamp"}`）（SHOULD）。

### 8.3 github（远程代码托管）

- 简单函数（MVP） MUST 提供：
  - `github(repo: str, path: str, *, ref: str|None=None, timeout: float|None=None, refresh: bool=False) -> str`（文本）。
  - `github.json(repo: str, path: str, *, ref: str|None=None, timeout: float|None=None, refresh: bool=False) -> dict|list`（JSON）。
- 未提供 `ref` 时 SHOULD 使用仓库默认分支；鉴权 SHOULD 通过 `CONSERVE_GITHUB_TOKEN`，令牌不得出现在日志（MUST NOT）。
- 限流/超时 MUST 显式抛出对应异常；可实现指数退避重试（SHOULD）。

### 8.4 http（通用 HTTP 客户端）

- `get(url: str, *, headers: dict|None=None, timeout: float|None=None, refresh: bool=False) -> bytes|str`（MUST）。
- `post/put/patch/delete(...)-> bytes|str`（SHOULD）。
- `json(url: str, ...) -> dict|list`（MUST），解析失败 MUST 抛 `TruthParseError`。
- 文本/二进制判定 SHOULD 依据 `Content-Type`，否则回退 UTF-8 文本。

### 8.5 docker（镜像与容器元信息）

- 无 Docker 环境时，对“本地”查询 MUST 抛 `TruthNotAvailable`；对“远程注册表”查询 SHOULD 正常工作（若实现）。
- `digest(image: str) -> str`（MUST，返回 `sha256:...`）。
- `labels(image: str) -> dict`、`size(image: str) -> int`（SHOULD）。
- `tags(repo: str) -> list[str]`、`latest_tag(repo: str) -> str|None`（SHOULD）。
- `local_images() -> list[str]`、`running_containers() -> list[dict]`（MAY）。

### 8.6 path（文件系统）

- `exists(p: PathLike) -> bool`、`is_file(...) -> bool`、`is_dir(...) -> bool`（MUST）。
- `size(p: PathLike) -> int`、`mtime(p: PathLike) -> datetime`（UTC）（SHOULD）。
- `hash(p: PathLike, algo: str="sha256") -> str`（MUST，算法名遵循 `hashlib`）。
- `glob(pattern: str) -> list[str]`、`find(root: PathLike, pattern: str) -> list[str]`（SHOULD）。

### 8.7 pypi（包索引）

- `version(pkg: str) -> str|None`、`latest(pkg: str) -> str|None`、`versions(pkg: str) -> list[str]`（MUST）。
- `info(pkg: str) -> dict`、`dependencies(pkg: str) -> list[str]`（SHOULD）。
- 应处理网络错误、不存在包名与速率限制（MUST）。

### 8.8 conda（Conda-PyPI 映射）

- MUST 提供：
  - `to_pypi(names: str|list[str]) -> str|list[str|None]`
  - `to_conda(names: str|list[str]) -> str|list[str|None]`
  - `search(pattern: str) -> dict[str,str]`
  - `mapping(conda_name: str) -> str|None`、`reverse_mapping(pypi_name: str) -> str|None`
  - `clear_cache() -> None`
- 参考实现基于 parselmouth 公共映射并使用 `urllib`（SHOULD）。缓存目录当前参考为 `/tmp/conserve`（MAY）；实现 SHOULD 支持通过 `CONSERVE_TRUTH_CACHE_DIR` 覆盖。

## 9. 配置、环境变量与默认值

- 全局缓存目录环境变量：`CONSERVE_TRUTH_CACHE_DIR`（SHOULD）。
- GitHub 鉴权：`CONSERVE_GITHUB_TOKEN`（SHOULD）。
- 默认网络超时 SHOULD 在 10–30 秒区间；实现 MAY 允许调用级覆盖。

## 10. 安全与合规

- 任何日志/异常信息 MUST NOT 泄露令牌、Cookie、隐私路径等敏感数据；必要时以 `***` 脱敏。
- 本地磁盘缓存文件 SHOULD 以仅用户可读写权限创建（如 `0o600`）。
- 远程访问 MUST 遵循最小权限原则；对写操作接口（若未来引入）本规范视为非目标（Out of Scope）。

## 11. 观测性与诊断

- 提供者 SHOULD 使用轻量日志（INFO 级别摘要、DEBUG 级别详细）；日志门面以标准库 `logging` 为主。
- 对 `timeout/retries/refresh` 的实际取值 SHOULD 在 DEBUG 级别输出，便于溯源；敏感头部 MUST 脱敏。

## 12. CLI 集成（可选）

- `conserve truth get <expr>`、`conserve truth cache <cmd>` 等子命令为可选（MAY）。若实现：
  - CLI 输出 MUST 为纯文本或 JSON（`--json`）。
  - 错误码：成功 `0`，用户可恢复错误 `2`，系统/网络错误 `3`（SHOULD）。

## 13. 稳定性、兼容性与弃用

- 新增 API SHOULD 标注稳定级别：`stable`、`experimental`。破坏性变更 MUST 采用弃用周期并在发行说明中说明替代方案。
- 版本遵循 SemVer（项目整体版本为准）。

## 14. 测试与验证

- 单元测试 MUST 覆盖：正常路径、错误模型（超时/未找到/未授权）与最小缓存行为；
- 端到端测试 SHOULD 在 `tests/test_e2e.py` 体现与任务集成；
- 不可访问真实互联网的场景 MUST 提供可模拟或跳过策略（如通过环境标志）。
- 运行命令：`pixi run pytest -q`；格式/静态检查：`pixi run pre-commit run -a`（MUST 通过）。

## 15. 编码与文档要求

- 代码 MUST 遵循项目风格（Ruff 行宽 120、现代类型、`pathlib`、f-string）。
- 仅在关键代码处添加英文注释（MUST），避免多余注释；遵循 DCY 原则。
- 模块与公共函数 MUST 提供清晰 docstring（英文），并在本规范对应章节登记其契约（contract）。

## 16. 参考最小示例（Informative）

> 以下示例仅用于说明形态；实现细节可根据环境调整。

```python
# conserve.truth.github – minimal surface
def github(repo: str, path: str, *, ref: str | None = None,
           timeout: float | None = None, refresh: bool = False) -> str: ...

def json(repo: str, path: str, *, ref: str | None = None,
         timeout: float | None = None, refresh: bool = False) -> dict | list: ...
```

```python
# conserve.truth.git – minimal surface
def branch() -> str: ...
def sha(short: bool = False) -> str: ...
def tag() -> str | None: ...
def dirty() -> bool: ...
def ahead() -> int: ...
def behind() -> int: ...
```

## 17. 合规清单（Checklist）

- 命名、参数与返回符合本规范（MUST）。
- 错误模型与异常类型符合预期（MUST）。
- 缓存行为与 `refresh` 语义正确（MUST）。
- 不泄露敏感信息；可配置缓存目录（MUST/SHOULD）。
- 提供足量测试与文档，CI 通过（MUST）。

— 规范结束 —

