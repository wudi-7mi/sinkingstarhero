# SinkingStarHero

独立版 Python/Tkinter GUI 修改器。它把 `sinking_star.CT` 中 Light abilities 的核心逻辑迁移到一个不依赖 Cheat Engine 的 Windows 小工具里。

运行时不需要安装 Cheat Engine，也不会连接 CE MCP 或其他 MCP 服务。

## 功能

- 自动检测并连接 `sinking_star.exe`
- 使用 AOB 签名与原始字节校验定位补丁点
- 支持接管上一次异常退出后留在游戏进程里的兼容 hook
- 提供 GUI 复选框和快捷键切换能力
- 提供玩家 XYZ 坐标读取/写入，坐标输入使用可步进的 Spinbox 控件

## 使用方法

1. 启动 **Order of the Sinking Star Demo**。
2. 运行 `SinkingStarHero.exe`。
3. 勾选能力，或使用快捷键切换：

```text
Ctrl+Alt+1  穿墙 / 绿光
Ctrl+Alt+2  开门 / 红光
Ctrl+Alt+3  粉碎 / 黄光
Ctrl+Alt+4  双倍 / 橙光
```

4. 在“角色坐标”区域点击“读取坐标”获取当前 XYZ。
5. 修改 X/Y/Z Spinbox 数值后点击“写入坐标”；“步进”控制上下箭头每次增减的幅度。

## 构建

`build/` 是本地构建产物目录，已经被 git 忽略，不会进入提交历史。

```powershell
.\build.ps1
```

构建完成后，可执行文件会生成到：

```text
build\SinkingStarHero.exe
```

## 诊断

如果 GUI 显示未连接，可以生成诊断日志：

```powershell
.\build\SinkingStarHero.exe --diagnose diagnose.txt
```

也可以调试 GUI 主循环状态：

```powershell
.\build\SinkingStarHero.exe --debug-log gui_debug.txt
```

## 支持版本

当前按本机 demo 版本制作。如果游戏更新后签名失效，工具会停止写入未知位置并显示错误。

## 注意

仅用于单机、离线调试或娱乐。

这类工具会修改另一个进程的内存，杀毒软件可能误报。如果无法连接游戏，请尝试以管理员身份运行本工具。

本项目不是 Thekla, Inc.、Jonathan Blow 或 Arc Games 的官方项目，也未获得官方背书。

## 开源协议

本项目使用 MIT License，详见 [LICENSE](LICENSE)。

## 致谢

感谢 **Thekla, Inc.** 与 **Jonathan Blow** 创作 **Order of the Sinking Star**。这个工具只是在单机环境下围绕 demo 做学习、调试和娱乐用途的轻量辅助。

感谢分析阶段用到的两个 MCP/工具链：

- **Cheat Engine MCP Bridge**：用于早期 Cheat Engine 表项、脚本和内存状态分析。
- **IDA Pro MCP**：用于反汇编、函数命名和关键逻辑定位。
