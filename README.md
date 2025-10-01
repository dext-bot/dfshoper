# 游戏商城自动助手

该工具提供图形界面，协助在游戏商城中自动识别并购买低价商品。所有图像识别基于 GPU 的 PaddleOCR 实现，以满足高性能要求。

## 功能概览

- **配置坐标**：支持在启动时或通过 UI 采集交易行、主界面、装备配置、购买按钮、最高购买数量按钮、商品价格位等关键坐标。
- **模式一**：循环检测商品价格 1、商品价格 2，当低于设定扫货价时自动点击最大购买数量与购买按钮。
- **模式二**：检测指定坐标的价格，高于阈值执行录制操作 1，低于阈值执行录制操作 2，并根据屏幕颜色判定是否停止。
- **录制导入**：动作录制以 JSON 格式导入，支持点击、移动、键盘输入、等待等操作。

## 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\\Scripts\\activate
pip install -r requirements.txt
```

> 💡 PaddleOCR 需要在安装了 CUDA 的环境中才能启用 GPU，请参考官方文档完成准备工作。

## 运行

```bash
python main.py --config path/to/config.json
```

首次运行如配置文件缺失，将弹出截图窗口供用户依次点击需要的坐标点。后续可在 UI 中继续调整并保存。

## 录制文件格式

录制动作以 JSON 数组表示，每个元素包含 `type` 与 `params` 字段，例如：

```json
[
  {"type": "click", "params": {"position": [120, 220]}},
  {"type": "sleep", "params": {"duration": 0.5}},
  {"type": "press", "params": {"key": "enter"}}
]
```

支持的 `type`：`click`、`double_click`、`right_click`、`move`、`press`、`write`、`sleep`。

## 注意事项

- 请确保以管理员权限运行，以便获得全屏截图与自动点击权限。
- 程序默认使用 F8 热键采集坐标，开始采集前会有 3 秒缓冲。
- 自动化操作存在风险，请在游戏允许的范围内使用。
