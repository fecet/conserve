# Conserve Package 模块 API 规范

> 本文档使用 RFC 2119/8174 术语（MUST/SHOULD/MAY）定义规范性要求。本规范定义 Package 模块的 API 接口，不涉及实现细节。

## 设计目标

Package 模块是**包元数据查询层**，基于 Package URL (PURL) 标准提供统一的版本、提交、日期等信息查询。

**核心原则**：

- **只读查询**：仅查询元数据，不修改包状态
- **错误处理**：区分两类情况
  - **错误**（网络故障、API 限流、权限拒绝等）：MUST 抛出异常
  - **数据缺失**（包不存在发布日期、仓库无 tag 等）：MAY 返回 None
- **类型安全**：返回结构化数据（`str` / `datetime` / `dict`）
- **实现无关**：本规范仅定义 API 行为，不规定实现方式

## API 设计

### 核心对象：Package

`Package` 是 Conserve 的核心对象之一（类似 `File`），封装包元数据查询能力。

```python
from conserve.package import Package

# 简洁格式（推荐）：type/name[@version]
pkg = Package("pypi/requests")
pkg = Package("pypi/requests@2.31.0")
pkg = Package("npm/lodash")
pkg = Package("github/user/repo@v1.0.0")

# 完整 PURL 格式（也支持）
pkg = Package("pkg:pypi/requests")
pkg = Package("pkg:npm/lodash@4.17.21")
```

**格式说明**：

- **简洁格式**（推荐）：`type/name[@version]` - 更易读，Conserve 内部自动补全 `pkg:` 前缀
- **完整 PURL**：`pkg:type/name[@version]` - 符合 PURL 规范，直接兼容外部工具
- 两种格式均可使用，API 自动识别

### 版本选择策略

```python
from typing import Literal, Self

# 版本选择策略类型定义
VersionStrategy = Literal[
    "latest_registry",      # PyPI/npm: 注册表标记的最新版本
    "latest_semver",        # 语义化版本最大值（默认忽略 pre-release）
    "latest_release",       # Git: 最新 Release（非草稿、非预发布）
    "latest_tag",           # Git: 最新 Tag（按提交时间）
    "latest_tag_semver",    # Git: Tag 中 SemVer 最大值（默认忽略 pre-release）
    "latest_commit",        # Git: 默认分支最新提交
]
```

**预发布版本处理**：

- `"latest_semver"` 和 `"latest_tag_semver"` 策略默认**忽略** pre-release 版本（如 `1.0.0-rc1`, `2.0.0-beta`）
- 仅当无稳定版本时，MAY 返回 pre-release 版本
- 版本比较 MUST 符合语义化版本规范（SemVer 2.0.0）

### 核心方法

```python
class Package:
    """包对象，封装 PURL 查询接口"""

    def latest(self, strategy: VersionStrategy | None = None) -> Self:
        """
        获取最新版本的 Package 对象

        Args:
            strategy: 版本选择策略，默认值根据包类型自动选择：
                - PyPI/npm: "latest_registry"
                - GitHub: "latest_release"（fallback 到 "latest_tag_semver"）

        Returns:
            带有 version 或 commit 的新 Package 对象
            - 对于版本策略（如 "latest_release"）：返回带 version 的对象
            - 对于 "latest_commit" 策略：返回的对象 MAY 无 version（仅 commit() 有效）
            - 数据缺失（无可用版本/release/tag）：抛出异常
            - 错误（网络故障等）：抛出异常

        Examples:
            pkg = Package("pypi/requests")
            latest = pkg.latest()  # Package("pypi/requests@2.31.0")

            repo = Package("github/user/repo")
            release = repo.latest("latest_release")  # 带 version
            commit = repo.latest("latest_commit")    # 可能无 version
        """

    def commit(self) -> str | None:
        """
        获取对应的 commit SHA（仅 Git 类型有效）

        适用场景：
        - 通过 tag/release 定位：返回对应的 commit SHA
        - 通过 commit 策略定位：返回该 commit SHA（即使无 version）
        - 通过 branch 定位：返回该分支 HEAD 的 commit SHA

        Returns:
            - 成功：完整 SHA（40 字符十六进制）
            - 数据缺失（非 Git 类型、无法解析引用）：None
            - 错误（网络故障等）：抛出异常
        """

    def date(self) -> datetime | None:
        """
        获取发布/提交日期（需 PURL 可解析到具体引用）

        支持的引用类型及对应日期：
        - PyPI/npm 版本号（如 2.31.0）：包发布日期
        - Git tag/release 名称：tag/release 创建日期
        - Git commit SHA（40 字符十六进制）：commit 日期
        - Git branch 名称：分支 HEAD commit 日期

        可通过 latest() 获取可定位的 Package，或直接指定：
        - Package("pypi/requests@2.31.0").date()
        - Package("github/user/repo@244fd47e...").date()
        - Package("github/user/repo@main").date()

        Returns:
            - 成功：timezone-aware UTC datetime（MUST 带时区）
            - 数据缺失（无法解析引用、包无发布日期）：None
            - 错误（网络故障等）：抛出异常
        """

    def info(self) -> dict | None:
        """
        获取完整元数据字典

        Returns:
            - 成功：包含包完整元数据的字典
              - PyPI/npm: 包含版本、作者、依赖等信息
              - Git: 包含 commit、author、message 等信息
              - 具体字段结构由包类型决定
            - 数据缺失（包不存在、无法解析引用）：None
            - 错误（网络故障等）：抛出异常
        """
```

### 使用示例

```python
from conserve.package import Package

# PyPI: 获取最新版本（推荐简洁格式）
pkg = Package("pypi/requests")
print(pkg.version)  # None（PURL 不带 version 字段）

latest = pkg.latest()  # 自动使用 "latest_registry" 策略
print(latest.version)  # "2.31.0"
print(latest.date())   # datetime(2023, 5, 22, ...)

# 检查指定版本
pkg = Package("pypi/requests@2.28.0")
print(pkg.version)  # "2.28.0"
print(pkg.date())   # datetime(2022, ...)

# Git: 不同策略获取版本
repo = Package("github/anthropics/anthropic-sdk-python")

# 最新 Release（推荐）
release = repo.latest("latest_release")
print(release.version)  # "v0.5.0"
print(release.commit()) # "abc123..."
print(release.date())   # datetime(2024, 1, 15, ...)

# 最新 Tag（按时间）
tag = repo.latest("latest_tag")
print(tag.version)  # "v0.6.0-beta"

# 最新 Tag（按 SemVer）
semver_tag = repo.latest("latest_tag_semver")
print(semver_tag.version)  # "v0.5.0"（忽略 beta 版本）

# 默认分支最新提交
commit = repo.latest("latest_commit")
print(commit.commit())  # "def456..."
print(commit.version)   # None（commit 没有 version 字段）

# 链式调用
date = Package("pypi/requests").latest().date()

# 完整 PURL 格式（也支持）
pkg = Package("pkg:pypi/requests")  # 与 "pypi/requests" 等效
```
