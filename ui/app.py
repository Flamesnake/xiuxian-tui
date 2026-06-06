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

    /* 主游戏网格 */
    #main-grid {
        layout: grid;
        grid-size: 3 1;
        grid-columns: 30 1fr 22;
        margin: 0 1;
        height: 1fr;
    }

    /* 左面板：状态 */
    #left-panel {
        border: solid green;
        padding: 0 1;
        height: 100%;
    }
    #left-panel > #status {
        height: auto;
    }

    /* 中面板：日志 */
    #center-panel {
        border: solid cyan;
        padding: 0 1;
        height: 100%;
    }
    #center-panel > #log {
        height: 100%;
    }

    /* 右面板：操作菜单 */
    #right-panel {
        border: solid yellow;
        padding: 0 1;
        height: 100%;
    }
    #right-panel > #actions {
        height: auto;
    }
    #right-panel Button {
        width: 100%;
        margin: 0 0 1 0;
    }

    /* 底部消息 */
    #message {
        background: #1a1a2e;
        color: #ccc;
        padding: 0 2;
        height: 3;
        dock: bottom;
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
