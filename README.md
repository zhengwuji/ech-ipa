# 网站监控与截图工具（全新版本）

> 适配 Windows 10，默认存档桌面 `jianche1` 文件夹；包含可视化 UI、区域选择、快捷键自定义、最小 60s 轮询监控，自动记录变化并截图留证。

## 功能概览
- 通过截图标记页面区域，OCR 识别区域文字（价格/销量/评价等）并监控变化。
- 变化时记录时间、旧值/新值、保存对应截图与 JSON 日志。
- 默认快捷键 F9，可自定义快捷键做手动截图留存。
- 可自定义监控间隔（>=60s）、保存路径、截图路径。
- Windows 10 风格 UI，支持一键选择监控区域。
- 版本号自动递增：`1.0.00` → `9.9.99`，后回到 `1.0.00` 循环。

## 安装与运行
1) 克隆仓库  
```bash
git clone https://github.com/zhengwuji/jianche1.git
cd jianche1
```

2) 安装依赖  
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

> 需要安装 Tesseract（用于 OCR），Windows 可从 https://github.com/UB-Mannheim/tesseract/wiki 安装，安装后确保 `tesseract.exe` 在 PATH。

3) 运行程序  
```bash
python main.py
```

## 使用步骤
1. 在“监控网址”输入商品链接（例：ebay 产品页）。
2. 设置检测间隔（最少 60s），保存路径与截图路径（默认桌面 `jianche1`）。
3. 点击“获取页面截图并选择区域”：
   - 程序会打开目标页截图。
   - 在截图上框选红色矩形区域（如价格区域）。
   - 保存后即为监控区域。
4. 点击“开始监控”，程序会定时截图并 OCR 识别区域文本，对比上一次的值。
5. 发生变化时：
   - 自动保存全页截图到截图路径。
   - 生成 JSON 日志到数据路径，包含时间、旧值/新值、截图路径、版本号。
6. 手动截图：按快捷键（默认 F9，可在 UI 修改）会将最近一次全页截图复制一份保存。

## 重要说明
- 最小监控间隔 60 秒，避免过于频繁请求。
- 若 OCR 识别不准，可适当放大区域或只框选数字部分。
- 初次运行需要下载 Playwright Chromium，时间视网络而定。
- 生成的配置保存在 `config.yaml`；版本号保存在 `version.json`。

## 打包为 exe
项目已配好 GitHub Actions（推送 main 自动打包并发布 Release）。本地可手动：
```bash
pip install pyinstaller
pyinstaller -F main.py -n jianche1
```
生成的 exe 位于 `dist/`，请在 Windows 10 上测试。

## 发布与版本
- 每次修改 `version.bump_version()` 会自动递增版本号；到 `9.9.99` 后回到 `1.0.00`。
- 推送到 main 后，GitHub Actions 会构建 exe 并发布到 Releases。

## 路径与存档
- 默认存档：`C:\Users\<用户名>\Desktop\jianche1`
- 子目录：
  - `screenshots`：页面截图
  - `saved_data`：变化日志（JSON）

## 常见问题
- **无法截图/浏览器错误**：确保执行过 `python -m playwright install chromium`。
- **OCR 无法识别中文**：安装 Tesseract 中文语言包，或调整区域更聚焦数字/价格文本。
- **快捷键冲突**：在 UI 修改为不冲突的组合键，如 `ctrl+shift+f9`。

## 开发提示
- UI 位于 `ui/`，核心监控逻辑在 `monitor.py`。
- 配置管理 `config.py`，版本管理 `version.py`。
- 修改后请运行 `version.bump_version()`（已在构建中调用）。

## 法律与合规
请遵守目标网站的服务条款与 robots.txt，合理设置检测间隔，仅用于合法用途。

