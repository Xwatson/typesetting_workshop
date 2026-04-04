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
