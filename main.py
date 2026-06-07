"""
修仙模拟器 — 终端 TUI 休闲游戏
在仪表盘式的终端界面中体验修仙世界。
"""

import io
import sys

# Windows 下强制 UTF-8 编码，确保 emoji 正常显示
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from ui.app import CultivationApp


def main():
    app = CultivationApp()
    app.run()


if __name__ == "__main__":
    main()
