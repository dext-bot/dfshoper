# DFShoper 自动低价购入工具

DFShoper 是一个面向 Windows 的游戏内商城自动化助手。它可以使用 GPU 加速的 OCR 识别商品价格，并按照用户配置自动执行扫货或策略化的脚本操作。

> **重要提示**
> - 程序仅用于个人效率提升，请确保遵守目标游戏的用户协议与相关法律法规。
> - 启动前请确保已经安装 NVIDIA 驱动与 CUDA，并正确安装了支持 GPU 的 PyTorch 以及 EasyOCR。

## 功能概述

- ⚙️ 启动时读取 `config/config.json`，自动恢复坐标及参数。
- 📸 如果缺少必要坐标，几秒后会弹出截图取点窗口，用户可以在截图上框选并保存坐标。
- 🧠 EasyOCR + GPU (PyTorch) 做价格数字识别。
- 🖱️ 两种自动化模式：
  - **模式一：扫货模式** — 监测多个商品的实时价格，低于自定义阈值时自动点击“最高数量”与“购买”按钮。
  - **模式二：策略模式** — 监测价格坐标并依据阈值执行两段录制操作，支持颜色判定终止条件。
- 🎯 UI 中所有坐标均可通过拖拽取点按钮快速标定。
- 🎞️ 内置鼠标键盘操作录制与回放。

## 快速开始

1. 创建虚拟环境并安装依赖：

   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate  # Windows PowerShell
   pip install -r requirements.txt
   ```

2. 复制 `config/default_config.json` 为 `config/config.json`，按需调整。
3. 运行程序：

   ```bash
   python -m dfshoper.app
   ```

## 依赖说明

- `PySide6` — 构建桌面 UI。
- `easyocr` — OCR 识别，需依赖支持 GPU 的 PyTorch。
- `mss` — 屏幕截图。
- `pyautogui`、`pynput` — 自动化输入与录制。
- `numpy`, `opencv-python-headless` — 图像预处理。

## 配置文件

配置文件采用 JSON 格式，主要分为以下几部分：

- `anchors`：交易行、主界面、配置装备、购买、最高数量、价格1、价格2 等核心坐标。
- `mode_one`：扫货模式下的项目列表与默认参数。
- `mode_two`：策略模式参数、录制脚本文件路径、终止条件等。

详细结构见 `config/default_config.json`。

## 录制脚本

录制脚本会保存在 `records/` 文件夹中，格式为 JSON，包含时间轴、鼠标键盘操作等信息。UI 中点击“录制操作1/2”后会先弹出保存路径对话框，选择完毕后程序会在 **3 秒倒计时** 后开始录制，录制期间按下 **F9** 即可结束并保存。程序可以在 UI 中播放录制脚本，用于模式二的自动化执行。

## 开发

项目采用模块化结构，主要代码位于 `src/dfshoper/`：

- `app.py` — 程序入口。
- `config.py` — 配置加载与保存。
- `ui/` — Qt UI 组件。
- `services/` — OCR、截图、操作录制等服务层。
- `modes/` — 模式一、模式二的业务逻辑。

欢迎根据自己的游戏和工作流程扩展项目。

