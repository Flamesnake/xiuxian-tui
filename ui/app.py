"""
Textual App 主类：应用配置、主题、CSS
"""

from __future__ import annotations

from textual.app import App
from textual.binding import Binding

from ui.screens import TitleScreen


class CultivationApp(App):
    """修仙模拟器 Textual App"""

    TITLE = "修仙模拟器"
    SUB_TITLE = "Cultivation Simulator v0.1"

    CSS = """
    /* 全局 */
    Screen {
        background: #0a0a0a;
    }

    /* 标题画面 */
    #title-container {
        align: center middle;
        width: 60;
        height: auto;
        padding: 2;
    }
    #title-container > #title-art {
        text-align: center;
        margin-bottom: 2;
    }
    #title-container > Button {
        width: 30;
        margin: 0 15 1 15;
    }

    /* ── 主游戏（命令输入模式） ── */

    /* 顶行：左状态 + 右主面板 */
    #top-row {
        layout: grid;
        grid-size: 2 1;
        grid-columns: 30 1fr;
        height: 1fr;            /* 占满日志和输入框之外的空间 */
        margin: 0 1;
    }

    #panel-status {
        border: solid green;
        padding: 0 1;
        height: 100%;
    }

    #panel-main {
        border: solid blue;
        padding: 0 1;
        height: 100%;
    }

    /* 历史日志 */
    #log {
        border: solid cyan;
        padding: 0 1;
        height: auto;
        max-height: 10;
        margin: 0 1;
    }

    /* 命令输入框 */
    #cmd-input {
        height: 3;
        margin: 0 1;
    }

    /* 底部状态栏 */
    #status-bar {
        background: #1a1a2e;
        color: #ccc;
        padding: 0 2;
        height: 1;
        dock: bottom;
        content-align: left middle;
    }

    /* 游戏结束 */
    #gameover-container {
        align: center middle;
        width: 60;
        height: auto;
        padding: 2;
    }
    #gameover-container > Static {
        text-align: center;
        margin-bottom: 1;
    }
    #gameover-container > Button {
        width: 30;
        margin: 0 15 1 15;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "退出", priority=True),
    ]

    def on_mount(self) -> None:
        self.push_screen(TitleScreen())
