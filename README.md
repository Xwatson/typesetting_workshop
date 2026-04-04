# 图片排版工坊

这是一个用于监听照片文件夹、在 A4 画布上进行图片排版预览、导出当前排版结果并直接调用打印机打印当前批次照片的桌面程序。

## 环境要求

- Python 3.13 或更高版本
- Windows 或 macOS

## Windows 安装与启动

1. 在项目根目录打开 PowerShell。
2. 创建虚拟环境：

```powershell
python -m venv .venv
```

3. 激活虚拟环境：

```powershell
.venv\Scripts\Activate.ps1
```

4. 安装项目及依赖：

```powershell
pip install -e .
```

5. 启动程序：

```powershell
python -m typesetting_workshop
```

也可以使用安装后的命令直接启动：

```powershell
typesetting-workshop
```

## macOS 安装与启动

1. 在项目根目录打开 Terminal。
2. 创建虚拟环境：

```bash
python3 -m venv .venv
```

3. 激活虚拟环境：

```bash
source .venv/bin/activate
```

4. 安装项目及依赖：

```bash
pip install -e .
```

5. 启动程序：

```bash
python -m typesetting_workshop
```

也可以使用安装后的命令直接启动：

```bash
typesetting-workshop
```

## 说明

- 程序会在用户应用数据目录中保存队列状态、程序设置以及导入后的图片副本。
- 如果项目里已经创建过 `.venv`，可以跳过创建虚拟环境这一步，直接激活后安装依赖或启动程序。

## 本地打包

项目已经内置了 `PyInstaller` 打包配置文件：

- `packaging/typesetting_workshop.spec`

先安装打包依赖：

```bash
pip install -e .[build]
```

然后执行打包：

```bash
pyinstaller --noconfirm --clean packaging/typesetting_workshop.spec
```

打包完成后，输出目录在：

- `dist/typesetting-workshop/`

Windows 下会生成 `typesetting-workshop.exe`，macOS 下会生成对应的应用目录内容。

## GitHub Actions 自动打包

项目已经提供 GitHub Actions 工作流：

- `.github/workflows/build-packages.yml`

这个工作流会在以下情况下运行：

- 手动触发 `workflow_dispatch`
- 推送标签，例如 `v0.1.0`

工作流会做这些事情：

1. 检出代码
2. 安装 Python 3.13
3. 安装项目依赖和打包依赖
4. 运行单元测试
5. 在 Windows 和 macOS 上分别执行 `PyInstaller`
6. 上传打包产物为 Actions Artifact

### 如何使用

1. 把当前项目推送到 GitHub 仓库。
2. 打开 GitHub 仓库页面。
3. 进入 `Actions` 标签页。
4. 选择 `Build Packages` 工作流。
5. 点击 `Run workflow` 手动执行。

执行完成后，你可以在该次工作流运行页面的 `Artifacts` 区域下载：

- `typesetting-workshop-Windows-archive`
- `typesetting-workshop-macOS-archive`

### 标签触发发布构建

如果你希望通过 Git 标签自动触发打包，可以执行：

```bash
git tag v0.1.0
git push origin v0.1.0
```

推送后，GitHub Actions 会自动开始构建。

### 关于 macOS 签名

当前工作流会生成未签名的 macOS 构建产物，适合内部测试和功能验证。

如果后续你要正式分发 macOS 应用，还需要额外配置：

- Apple Developer 证书
- 签名与公证流程
- GitHub Secrets

如果你需要，我下一步可以继续帮你把：

- Windows 图标与版本信息
- macOS `.app` 包优化
- GitHub Release 自动上传
- macOS 签名/公证工作流

一起补上。
