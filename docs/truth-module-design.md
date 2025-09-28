# Truth 模块设计文档

## 概述

Truth 模块为 Conserve 提供从各种来源获取数据的能力：主机环境、Git 仓库、GitHub、Docker Registry 等。设计理念是**简单、直接、实用**。

## 设计原则

1. **简单优先**：能用函数解决的不用类，能直接返回的不用包装
2. **各自最优**：不同数据源采用最适合的 API 设计，不强求统一
3. **显式缓存**：缓存是可选的，需要时显式启用
4. **零配置**：开箱即用，高级功能可选配置

## API 设计

### 主机信息 (truth.host)

直接返回值的简单函数：

```python
from conserve import truth

# 系统信息
platform = truth.host.platform()        # "linux", "darwin", "windows"
arch = truth.host.arch()                # "x86_64", "arm64"
hostname = truth.host.hostname()        # "dev-machine"
user = truth.host.user()                # "john"
home = truth.host.home()                # "/home/john"

# Python 环境
python = truth.host.python()            # "3.12.1"
python_version = truth.host.python_version()  # (3, 12, 1)
venv = truth.host.venv()                # "/path/to/venv" or None

# 环境变量
env = truth.host.env("PATH")            # "/usr/bin:/usr/local/bin:..."
env = truth.host.env("MISSING", default="default_value")

# 检查命令是否存在
has_docker = truth.host.has_command("docker")  # True/False
```

### Git 信息 (truth.git)

当前仓库的信息：

```python
# 基本信息
branch = truth.git.branch()             # "main"
sha = truth.git.sha()                   # "abc123def456..."
sha_short = truth.git.sha(short=True)   # "abc123d"
tag = truth.git.tag()                   # "v1.2.3" or None

# 状态
dirty = truth.git.dirty()               # True if uncommitted changes
ahead = truth.git.ahead()               # 3 (commits ahead of remote)
behind = truth.git.behind()             # 0 (commits behind remote)

# 远程信息
remote = truth.git.remote()             # "origin"
remote_url = truth.git.remote_url()     # "git@github.com:user/repo.git"

# 作者信息
author = truth.git.author()             # "John Doe"
email = truth.git.email()               # "john@example.com"

# 最近提交
last_commit = truth.git.last_commit()   # {"sha": "...", "message": "...", "author": "..."}
```

### GitHub (truth.github)

简单用法 - 直接获取文件：

```python
# 获取文件内容（文本）
content = truth.github("org/repo", "README.md")
config = truth.github("org/repo", "config.toml", ref="v1.0.0")

# 获取 JSON 并解析
data = truth.github.json("org/repo", "package.json")
```

复杂用法 - 使用 GitHub 类：

```python
# 创建 GitHub 实例（可选认证）
gh = truth.GitHub("org/repo", token=truth.host.env("GITHUB_TOKEN"))

# 文件操作
readme = gh.file("README.md")
config = gh.file("config/app.toml", ref="develop")

# 获取发布信息
latest = gh.latest_release()            # {"tag": "v1.2.3", "name": "...", ...}
releases = gh.releases()                # [{"tag": "v1.2.3", ...}, ...]

# 获取标签
tags = gh.tags()                         # ["v1.2.3", "v1.2.2", ...]

# 目录列表
files = gh.ls("src/")                   # ["main.py", "utils.py", ...]
```

### HTTP 请求 (truth.http)

简单的 HTTP 客户端：

```python
# GET 请求
data = truth.http.get("https://api.example.com/config")
data = truth.http.get(url, headers={"Authorization": "Bearer token"})

# POST 请求
result = truth.http.post(url, json={"key": "value"})
result = truth.http.post(url, data="raw data", headers={...})

# 其他方法
truth.http.put(url, json={...})
truth.http.delete(url)
truth.http.patch(url, json={...})

# 直接获取 JSON
config = truth.http.json("https://api.example.com/config.json")

# 下载文件
truth.http.download("https://example.com/file.zip", "local.zip")
```

### Docker Registry (truth.docker)

镜像和容器信息：

```python
# 镜像信息
digest = truth.docker.digest("python:3.12")          # "sha256:abc123..."
labels = truth.docker.labels("myapp:latest")         # {"version": "1.0", ...}
size = truth.docker.size("alpine:latest")            # 5242880 (bytes)

# 标签
tags = truth.docker.tags("python")                   # ["3.12", "3.12-slim", ...]
latest = truth.docker.latest_tag("myapp")            # "v1.2.3"

# 本地 Docker
images = truth.docker.local_images()                 # ["python:3.12", ...]
running = truth.docker.running_containers()          # [{"name": "web", ...}, ...]
```

### 文件系统 (truth.path)

路径和文件信息：

```python
# 存在性检查
exists = truth.path.exists("/etc/hosts")
is_file = truth.path.is_file("config.toml")
is_dir = truth.path.is_dir("/home/user")

# 文件信息
size = truth.path.size("data.json")                  # bytes
mtime = truth.path.mtime("config.toml")             # datetime
hash = truth.path.hash("file.bin", "sha256")        # "abc123..."

# 查找文件
files = truth.path.glob("*.py")                      # ["main.py", "test.py", ...]
files = truth.path.find("src/", "*.test.js")        # 递归查找
```

### PyPI (truth.pypi)

Python 包信息：

```python
# 包信息
version = truth.pypi.version("requests")             # "2.31.0"
latest = truth.pypi.latest("django")                 # "5.0.1"
versions = truth.pypi.versions("flask")              # ["3.0.0", "2.3.3", ...]

# 包元数据
info = truth.pypi.info("pandas")                     # {"author": "...", "license": "...", ...}
deps = truth.pypi.dependencies("fastapi")            # ["pydantic>=2.0", "starlette", ...]
```

## 与 Conserve 集成

### 基本用法

```python
# .conserve/truth_sync.py

from conserve import truth, TOMLHandle, YAMLHandle

def conserve_sync_python_version():
    """更新 pyproject.toml 中的 Python 版本要求"""
    py_ver = truth.host.python()  # "3.12.1"
    major, minor = py_ver.split(".")[:2]

    TOMLHandle("pyproject.toml").load().merge({
        "project": {
            "requires-python": f">={major}.{minor}"
        }
    }).save()

def conserve_sync_from_template():
    """从 GitHub 模板同步配置"""
    # 直接获取文件内容
    ruff_config = truth.github("org/python-template", "ruff.toml")
    TOMLHandle("ruff.toml").replace(ruff_config).save()

    # 获取 JSON 配置
    prettier_config = truth.github.json("org/js-template", ".prettierrc")
    JSONHandle(".prettierrc").replace(prettier_config).save()

def conserve_pin_docker_images():
    """将 Docker 镜像标签替换为摘要"""
    compose = YAMLHandle("docker-compose.yml").load()
    services = compose.read()["services"]

    for service_name, service in services.items():
        if "image" in service:
            image = service["image"]
            # 将 image:tag 转换为 image@digest
            digest = truth.docker.digest(image)
            base_image = image.split(":")[0]
            service["image"] = f"{base_image}@{digest}"

    compose.save()

def conserve_update_deps_from_pypi():
    """更新依赖到最新版本"""
    config = TOMLHandle("pyproject.toml").load()
    deps = config.read().get("project", {}).get("dependencies", [])

    updated_deps = []
    for dep in deps:
        # 解析包名（简化示例）
        pkg_name = dep.split(">=")[0].split("==")[0].strip()
        latest = truth.pypi.latest(pkg_name)
        updated_deps.append(f"{pkg_name}>={latest}")

    config.merge({
        "project": {"dependencies": updated_deps}
    }).save()
```

### 高级用法

```python
def conserve_build_deployment_manifest():
    """构建部署清单，包含各种元信息"""
    manifest = {
        "metadata": {
            "built_by": truth.host.user(),
            "built_on": truth.host.hostname(),
            "platform": f"{truth.host.platform()}/{truth.host.arch()}",
            "timestamp": truth.timestamp(),
        },
        "git": {
            "branch": truth.git.branch(),
            "commit": truth.git.sha(short=True),
            "dirty": truth.git.dirty(),
        },
        "python": {
            "version": truth.host.python(),
            "venv": truth.host.venv(),
        },
        "docker": {
            "images": {},
        }
    }

    # 添加 Docker 镜像信息
    for image in ["redis:7", "postgres:16", "nginx:alpine"]:
        manifest["docker"]["images"][image] = {
            "digest": truth.docker.digest(image),
            "size": truth.docker.size(image),
        }

    YAMLHandle("deployment.yaml").replace(manifest).save()

def conserve_validate_environment():
    """验证开发环境是否满足要求"""
    errors = []

    # 检查 Python 版本
    py_ver = truth.host.python_version()
    if py_ver < (3, 10):
        errors.append(f"Python {py_ver} is too old, need >= 3.10")

    # 检查必需的命令
    for cmd in ["git", "docker", "make"]:
        if not truth.host.has_command(cmd):
            errors.append(f"Missing required command: {cmd}")

    # 检查环境变量
    for var in ["GITHUB_TOKEN", "DOCKER_REGISTRY"]:
        if not truth.host.env(var):
            errors.append(f"Missing environment variable: {var}")

    # 检查 Git 状态
    if truth.git.dirty():
        errors.append("Git repository has uncommitted changes")

    if errors:
        print("❌ Environment validation failed:")
        for error in errors:
            print(f"  - {error}")
        exit(1)
    else:
        print("✅ Environment validation passed")
```

## 缓存（可选功能）

默认情况下，truth 函数不缓存。需要缓存时显式启用：

### 使用装饰器

```python
from conserve.truth import cached

@cached(ttl=3600)  # 缓存 1 小时
def get_github_config():
    return truth.github("org/repo", "config.toml")

# 使用时自动缓存
config = get_github_config()  # 第一次从 GitHub 获取
config = get_github_config()  # 第二次从缓存读取
```

### 使用上下文管理器

```python
from conserve.truth import cache

# 在上下文中的所有调用都会缓存
with cache(ttl=900):  # 15 分钟
    config1 = truth.github("org/repo", "file1.toml")
    config2 = truth.github("org/repo", "file2.toml")
    # 相同调用会使用缓存
    config1_again = truth.github("org/repo", "file1.toml")  # 从缓存

# 清除缓存
truth.cache.clear()
truth.cache.clear("github")  # 只清除 GitHub 相关缓存
```

### 手动缓存控制

```python
# 强制刷新（忽略缓存）
content = truth.github("org/repo", "file.toml", refresh=True)

# 检查缓存状态
size = truth.cache.size()  # 缓存大小（字节）
count = truth.cache.count()  # 缓存项数量
truth.cache.info()  # 打印缓存信息
```

## CLI 集成

虽然 truth 主要通过 Python API 使用，但也提供一些 CLI 命令用于调试：

```bash
# 获取并显示数据
conserve truth get host.platform
conserve truth get git.branch
conserve truth get github:org/repo:README.md

# 缓存管理
conserve truth cache info       # 显示缓存信息
conserve truth cache clear      # 清除所有缓存
conserve truth cache clear github  # 清除特定类型缓存

# 在任务中使用
conserve run --refresh-cache    # 运行前清除缓存
```

## 实现计划

### Phase 1：核心功能（第 1 周）
- [ ] 基础模块结构
- [ ] truth.host 实现
- [ ] truth.git 实现
- [ ] 基本测试

### Phase 2：外部数据源（第 2-3 周）
- [ ] truth.github 实现
- [ ] truth.http 实现
- [ ] truth.docker 实现
- [ ] 错误处理和重试

### Phase 3：辅助功能（第 4 周）
- [ ] truth.path 实现
- [ ] truth.pypi 实现
- [ ] 缓存系统
- [ ] CLI 命令

### Phase 4：优化和文档（第 5 周）
- [ ] 性能优化
- [ ] 完整文档
- [ ] 示例集合
- [ ] 集成测试

## 配置（可选）

大多数情况下无需配置。如需自定义：

```toml
# ~/.config/conserve/truth.toml 或项目根目录 .conserve.toml

[truth.cache]
enabled = true
directory = "~/.cache/conserve/truth"
default_ttl = 900  # 秒

[truth.github]
token = "${GITHUB_TOKEN}"  # 使用环境变量
api_url = "https://api.github.com"  # 企业版 GitHub

[truth.docker]
registry = "registry.example.com"
```

或通过环境变量：

```bash
export CONSERVE_TRUTH_CACHE_DIR="/tmp/conserve"
export CONSERVE_GITHUB_TOKEN="ghp_xxxx"
```

## 设计理念总结

1. **实用主义**：解决实际问题，不过度设计
2. **零摩擦**：简单任务应该简单，复杂任务应该可能
3. **渐进增强**：基础功能开箱即用，高级功能按需启用
4. **明确清晰**：API 名称直观，行为可预测

这个设计让 truth 模块既简单易用，又足够强大以应对复杂场景。