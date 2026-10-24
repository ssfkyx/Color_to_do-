# ColourTodo · 色彩待办

<p align="center">
  <b>中文</b> · <a href="#english">English</a>
</p>

<p align="center">
  <img alt="Platform: Windows 10/11" src="https://img.shields.io/badge/platform-Windows%2010%2F11-0078D4">
  <img alt="Python 3.12" src="https://img.shields.io/badge/python-3.12-3776AB">
  <img alt="Tests: 32 passing" src="https://img.shields.io/badge/tests-32%20passing-2ea44f">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green">
</p>

A local-first Windows todo app: type a task, drag it onto a 24-hour calendar, and get a tray reminder when it is due. No account, no cloud, no network.

一个本地优先的 Windows 桌面待办应用：输入一句话，拖到 24 小时时间轴，到点用托盘弹窗提醒。不需要账号，不联网，不上传数据。

![日视图](design/ui_main.png)

---

## 中文

### 简介

色彩待办用 Python + Tkinter 写成，发布为免安装的 Windows onedir ZIP。数据保存在本机 JSON 文件里，适合个人日常使用，也适合想读一份完整桌面 app 代码的人。

### 功能

- **输入即待办**：左侧输入，Enter / 小键盘 Enter / 右侧 `＋` 固化。
- **右键管理**：待安排卡片右键可修改 / 删除；时间轴事件右键可删除。
- **拖拽排期**：把卡片拖到 24 小时时间轴，按 15 分钟吸附；拖动过程中在吸附落点显示横线与时间，松手前就能确认会排到几点。
- **三种视角**：日 / 周 / 月自由切换；周、月视图点击任意日期进入日视图。
- **今天**：无论在周/月视图，点「今天」都会回到今天的日视图。
- **到点提醒**：60 秒置顶卡片，两个按钮：
  - **做**：完成并保留记录，可在「已完成」页签查看。
  - **拖**：打开日视图并高亮任务，拖到新时间即可改期。
  - 60 秒无操作：自动关闭，5 分钟后再提醒。
- **托盘常驻**：关闭主窗口时，托盘可用就收起到通知区域；托盘不可用则直接退出，不会把窗口藏到找不到的地方。
- **macOS 风格窗口控制**：左上角红黄绿三个圆点，分别关闭 / 最小化 / 最大化；无边框窗口可拖动、可缩放。
- **本地保存**：JSON 文件，重启恢复；已完成记录永久保留。
- **单实例**：重复双击 exe 会唤醒已运行窗口，即使它已收起。
- **透明工程结构**：核心模型不依赖 Tk；外观集中在主题文件；浮点几何统一用 FP64 别名/辅助函数。

### 截图

| 拖拽落点预览 | 提醒弹窗 |
|---|---|
| ![拖拽落点](design/ui_drag_preview.png) | ![提醒弹窗](design/ui_reminder.png) |

| 周视图 | 月视图 |
|---|---|
| ![周视图](design/ui_week.png) | ![月视图](design/ui_month.png) |

### 下载与运行

**推荐方式：GitHub Releases**

1. 打开仓库的 **Releases** 页面。
2. 下载最新的 `ColourTodo-win64.zip`。
3. 解压到任意可写目录。
4. 运行 `ColourTodo\ColourTodo.exe`。

请注意：`ColourTodo.exe` 必须和 `_internal` 文件夹放在同一层，不要只复制 exe。

要求：Windows 10/11。发布包已包含 Python 运行时，不需要安装 Python。

### 从源码运行

要求 Windows 10/11 + Python 3.12。

```powershell
git clone <repository-url>
cd colour-todo

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

也可以：

```powershell
.\.venv\Scripts\python.exe -m colour_todo
```

### 使用

| 操作 | 结果 |
|---|---|
| 输入后 Enter / 小键盘 Enter / `＋` | 新增待办 |
| 右键待安排卡片 | 修改 / 删除 |
| 拖左侧卡片到日视图 | 排期 |
| 拖日视图事件条 | 改时间 |
| 右键时间轴事件 | 删除 |
| 日 / 周 / 月 | 切换视角 |
| `‹` `›` | 按当前视角前后移动 |
| 今天 | 一键回到今天的日视图 |
| 关闭窗口 | 红点：托盘可用时收起，不可用时退出 |
| 最小化 | 黄点：最小化到任务栏 |
| 最大化 / 还原 | 绿点，或双击标题栏 |
| 退出程序 | 托盘菜单「退出」、`Ctrl+Q`，或右键任务栏「关闭窗口」 |
| 移动窗口 | 拖动标题栏空白处 |
| 缩放窗口 | 拖动右下角把手 |
| 提醒 → 做 | 完成，写入已完成记录 |
| 提醒 → 拖 | 打开日视图并高亮，等用户改期 |

### 提醒规则

- 到 `remind_at` 时弹出一个 60 秒的置顶卡片。
- **做**：标记完成，保留完成时间；不再提醒。
- **拖**：窗口打开到日视图并高亮任务，把事件条拖到新时间即可重新排期。
- 60 秒内没有操作：自动关闭，5 分钟后再次提醒。
- 提醒依赖应用进程存活；从托盘退出后不会提醒。
- `remind_at` 会持久化，重启应用后会继续检查到期的提醒。

### 托盘图标

- 关闭窗口后，图标在 Windows 通知区域；Windows 11 默认放在 `^`「显示隐藏的图标」里。
- 图标使用固定 GUID，Windows 会把它当作同一个应用，记住你把它放在可见区还是隐藏区。第一次如果出现在可见区，拖到 `^` 一次即可。
- 如果通知区域不可用（例如 Explorer 未运行 / 权限被拒），红点关闭会直接退出；右键任务栏「关闭窗口」、`Alt+F4`、`Ctrl+Q` 也始终可以退出。
- 双击 exe 会唤醒已运行窗口，即使它已经收起。

> Windows 11 的「显示隐藏的图标」由系统管理，应用不能强制把自己塞进去。第一次如果图标出现在可见区，把它拖进 `^` 一次；之后固定 GUID 会让 Windows 记住这个选择。也可以在「设置 → 个性化 → 任务栏 → 其他系统托盘图标」里调整。

### 数据与隐私

默认路径：

```text
%LOCALAPPDATA%\ColourTodo\todos.json
```

- 每个 Windows 用户独立，升级 exe 不影响数据。
- 如果 `%LOCALAPPDATA%` 不可写，程序会依次退到 `%USERPROFILE%\ColourTodoData`、exe 同目录的 `ColourTodoData`；实际路径写在数据目录的 `app.log` 里。
- 可用 `--data-dir <目录>` 指定其他位置（便携模式 / 测试）。
- 一条 Todo 约 250–350 字节，10,000 条约 3 MB。
- 应用不联网、不需要账号、没有遥测；数据只在本机。
- 备份：关闭应用后复制 `todos.json` 即可。
- 仓库不包含用户数据；`.gitignore` 已排除 `todos.json`、`app.log`、`ColourTodoData/` 等。

### 构建 Windows exe

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\tools\build_exe.ps1
```

输出：

```text
dist\ColourTodo\ColourTodo.exe
dist\ColourTodo-win64.zip
```

采用 **onedir**，不做 onefile 临时解压，启动更稳，也避免受限 `%TEMP%` 下的 `Could not create temporary directory!`。

`dist/` 默认被 `.gitignore` 忽略；发布时把 `ColourTodo-win64.zip` 作为 GitHub Release 附件，不提交构建产物。

### 测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

当前 32 项通过：核心模型 / 提醒状态 / JSON / 日期运算 / 事件分栏，以及 Tk 的输入、三视图、拖拽、右键、提醒「做 / 拖 / 超时」。

GitHub Actions 在 Windows 上运行核心测试；UI 测试会创建真实 Tk 窗口，建议在本地交互式 Windows 桌面运行。

### 项目结构

```text
colour_todo/
  core/         # Todo、TimeSlot、服务、提醒查询（无 Tk）
  infra/        # JSON、时钟、单实例、托盘
  ui/           # Tk 界面、主题、拖拽、弹窗、编辑对话框
  config.py     # 行为 / 路径配置
  fp64.py       # FP64 约定
tests/          # unittest：核心 + Tk UI
tools/          # 打包、图标、截图
design/         # 实际 UI 截图
docs/           # 发布说明
tracer/         # tracer bullet 原型（保留作证据）
pre_architecture.md
```

### 设计说明

- 核心层不导入 Tkinter；UI 只通过 `TodoService` / `ReminderService` 改状态。
- 外观参数集中在 `colour_todo/ui/theme.py`；行为与路径在 `config.py`。
- 浮点几何统一通过 `colour_todo/fp64.py` 的 `FP64` / `fp64()`，避免隐式单精度。
- 更完整的类图、模块边界、提醒状态机和数据格式见 [pre_architecture.md](pre_architecture.md)。

### 已知限制

- 仅支持 Windows 10/11。
- 不做云同步、账号、多人协作。
- 周 / 月视图只读；点击日期进入日视图后再拖。
- 事件时长默认 30 分钟，当前不支持拖拽调整时长；改期会保留原时长。
- 托盘图标在「显示隐藏的图标」中的位置由 Windows 管理，应用不能强制放入。
- 应用不自动开机启动；需要常驻提醒时请让托盘进程保持运行。
- 没有导入 / 导出、重复任务、子任务等高级功能。

### 贡献

欢迎提 Issue / PR。提交前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)；发布流程见 [docs/RELEASING.md](docs/RELEASING.md)。

### License

[MIT](LICENSE) © 2026 ColourTodo contributors

---

<a id="english"></a>

## English

### What it is

ColourTodo is a local-first Windows todo app built with Python and Tkinter. Type a task, drag it onto a 24-hour calendar, and get a tray reminder when it is due. There is no account, no cloud sync, and no network access.

It ships as a portable onedir ZIP and stores everything in a local JSON file.

### Features

- **Type to capture**: press Enter, numpad Enter, or the `＋` button.
- **Right-click management**: edit or delete an unscheduled card; delete a scheduled event.
- **Drag scheduling**: drop a card onto the 24-hour timeline with 15-minute snapping. While dragging, a horizontal line and time label preview the exact drop position.
- **Day / week / month views**: switch freely; clicking a date in week/month opens the day view.
- **Today**: always returns to today's day view, even from week/month.
- **Reminders**: a 60-second topmost card with two actions:
  - **Done**: complete the task and keep a completed record.
  - **Reschedule**: open the day view, highlight the task, and drag it to a new time.
  - No action for 60 seconds: close and remind again after 5 minutes.
- **Tray resident**: closing the main window hides it to the notification area when the tray is available; if the tray cannot be registered, closing exits instead of hiding the window somewhere unreachable.
- **macOS-style window controls**: red/yellow/green dots for close / minimize / maximize; the frameless window can be dragged and resized.
- **Local persistence**: JSON file; state survives restarts; completed records are retained.
- **Single instance**: launching the exe again activates the existing window, even when hidden.
- **Transparent architecture**: the core does not depend on Tk; appearance lives in the theme; floating-point geometry uses the FP64 alias/helpers.

### Screenshots

| Drag preview | Reminder |
|---|---|
| ![Drag preview](design/ui_drag_preview.png) | ![Reminder](design/ui_reminder.png) |

| Week view | Month view |
|---|---|
| ![Week view](design/ui_week.png) | ![Month view](design/ui_month.png) |

### Download and run

**Recommended: GitHub Releases**

1. Open the repository's **Releases** page.
2. Download the latest `ColourTodo-win64.zip`.
3. Extract it to a writable folder.
4. Run `ColourTodo\ColourTodo.exe`.

Keep `ColourTodo.exe` next to the `_internal` folder; do not copy the exe alone.

Requires Windows 10/11. The release bundle includes the Python runtime, so Python is not required.

### Run from source

Requires Windows 10/11 and Python 3.12.

```powershell
git clone <repository-url>
cd colour-todo

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Or:

```powershell
.\.venv\Scripts\python.exe -m colour_todo
```

### Usage

| Action | Result |
|---|---|
| Enter / numpad Enter / `＋` | Add a todo |
| Right-click an unscheduled card | Edit / delete |
| Drag a card to the day view | Schedule |
| Drag a day-view event | Reschedule |
| Right-click a timeline event | Delete |
| Day / Week / Month | Switch view |
| `‹` `›` | Move backward / forward in the current view |
| Today | Return to today's day view |
| Close | Red dot: hide to tray when available, otherwise exit |
| Minimize | Yellow dot: minimize to taskbar |
| Maximize / restore | Green dot, or double-click the title bar |
| Quit | Tray menu "Quit", `Ctrl+Q`, or right-click taskbar → Close |
| Move window | Drag empty title-bar space |
| Resize window | Drag the bottom-right grip |
| Reminder → Done | Complete and write a completed record |
| Reminder → Reschedule | Open the day view and highlight the task |

### Reminder behaviour

- At `remind_at`, a 60-second topmost card appears.
- **Done** marks the task complete and keeps the completion time; no further reminders.
- **Reschedule** opens the day view and highlights the task. Drag the event to a new time to re-arm the reminder.
- No action for 60 seconds: close and remind again after 5 minutes.
- Reminders require the process to be running; quitting from the tray stops them.
- `remind_at` is persisted, so due reminders are checked again after a restart.

### Tray icon

- After closing the window, the icon lives in the Windows notification area; Windows 11 usually puts it under `^` (hidden icons).
- A stable GUID lets Windows remember whether you placed it in the visible area or the hidden area. If it first appears in the visible area, drag it into `^` once.
- If the notification area is unavailable (for example Explorer is not running or access is denied), the red close dot exits instead of hiding; taskbar Close, `Alt+F4`, and `Ctrl+Q` always exit.
- Launching the exe again activates the existing window, including a hidden one.

> Windows 11 controls the hidden-icons area; an app cannot force itself into it. If the icon appears in the visible area, drag it into `^` once. Windows should remember the choice for the stable GUID. You can also adjust it in Settings → Personalization → Taskbar → Other system tray icons.

### Data and privacy

Default path:

```text
%LOCALAPPDATA%\ColourTodo\todos.json
```

- Per Windows user; upgrading the exe does not touch the data.
- If `%LOCALAPPDATA%` is not writable, the app falls back to `%USERPROFILE%\ColourTodoData`, then `ColourTodoData` next to the exe; the actual path is written to `app.log`.
- Use `--data-dir <folder>` for a portable or test location.
- About 250–350 bytes per todo; roughly 3 MB for 10,000 todos.
- No network, no account, no telemetry; data stays on the machine.
- Backup: close the app and copy `todos.json`.
- The repository never contains user data; `.gitignore` excludes `todos.json`, `app.log`, `ColourTodoData/`, and related files.

### Build the Windows exe

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\tools\build_exe.ps1
```

Outputs:

```text
dist\ColourTodo\ColourTodo.exe
dist\ColourTodo-win64.zip
```

The distribution is **onedir**, not onefile: it avoids temporary extraction and the `Could not create temporary directory!` failure in restricted `%TEMP%` environments.

`dist/` is git-ignored. Attach `ColourTodo-win64.zip` to a GitHub Release; do not commit build output.

### Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

32 tests currently pass: core model / reminder state / JSON / date arithmetic / event lanes, plus Tk input, three views, drag, right-click actions, and reminder Done/Reschedule/timeout.

GitHub Actions runs the core tests on Windows. The UI tests create real Tk windows and are intended for an interactive Windows desktop.

### Project layout

```text
colour_todo/
  core/         # Todo, TimeSlot, services, reminder queries (no Tk)
  infra/        # JSON, clock, single instance, tray
  ui/           # Tk widgets, theme, drag, popups, edit dialog
  config.py     # behaviour and path configuration
  fp64.py       # FP64 convention
tests/          # unittest: core + Tk UI
tools/          # packaging, icon, screenshots
design/         # live UI screenshots
docs/           # release notes
tracer/         # tracer-bullet prototype, kept as evidence
pre_architecture.md
```

### Design notes

- The core layer does not import Tkinter; the UI mutates state only through `TodoService` / `ReminderService`.
- Appearance belongs in `colour_todo/ui/theme.py`; behaviour and paths belong in `config.py`.
- Floating-point geometry goes through `FP64` / `fp64()` in `colour_todo/fp64.py`.
- See [pre_architecture.md](pre_architecture.md) for the class diagram, module boundaries, reminder state machine, and data format.

### Known limitations

- Windows 10/11 only.
- No cloud sync, account, or collaboration.
- Week/month views are read-only; click a date to open the day view before dragging.
- Event duration defaults to 30 minutes and cannot be resized yet; rescheduling preserves the existing duration.
- The tray icon's location in the hidden-icons area is controlled by Windows.
- No auto-start on login; keep the tray process running for reminders.
- No import/export, recurring tasks, or subtasks yet.

### Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/RELEASING.md](docs/RELEASING.md).

### License

[MIT](LICENSE) © 2026 ColourTodo contributors
