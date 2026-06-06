"""
自定义 Textual 组件：状态面板、日志面板、操作菜单、消息栏
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.reactive import reactive
from textual.widgets import Static, Button, RichLog
from textual.containers import Vertical, Horizontal
from textual.widget import Widget
from rich.text import Text
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table

from game.config import REALMS, cultivation_needed
from game.state import PlayerState, num_to_cn

if TYPE_CHECKING:
    pass


class StatusPanel(Static):
    """角色状态面板：显示境界、气血、灵气、修为、寿元等"""

    def __init__(self, state: PlayerState, **kwargs):
        super().__init__(**kwargs)
        self.state = state

    def refresh_state(self, state: PlayerState) -> None:
        self.state = state
        self.update_render()
        self.refresh()

    def on_mount(self) -> None:
        self.update_render()

    def update_render(self) -> None:
        s = self.state
        if not s:
            self.update("[red]加载中...[/]")
            return

        grid = Table.grid(padding=(0, 1), expand=True)
        grid.add_column(justify="left", ratio=1)

        # 境界
        grid.add_row(f"{s.realm_icon} [bold yellow]{s.realm_name}[/] {num_to_cn(s.layer)}层")

        # 修为进度
        needed = s.cultivation_max
        ratio = s.cultivation_progress
        bar_len = 20
        filled = int(ratio * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        grid.add_row(f"修为  {bar} [green]{ratio*100:.0f}%[/]")
        grid.add_row(f"      [dim]{s.cultivation}/{needed}[/]")

        # 气血
        hp_r = s.hp / s.max_hp if s.max_hp > 0 else 0
        hp_bar = _health_bar(hp_r, 20)
        hp_color = "green" if hp_r > 0.5 else ("yellow" if hp_r > 0.2 else "red")
        grid.add_row(f"气血  {hp_bar} [{hp_color}]{s.hp}/{s.max_hp}[/]")

        # 灵气
        qi_r = s.qi / s.max_qi if s.max_qi > 0 else 0
        qi_bar = _qi_bar(qi_r, 20)
        qi_color = "cyan" if qi_r > 0.3 else "blue"
        grid.add_row(f"灵气  {qi_bar} [{qi_color}]{s.qi}/{s.max_qi}[/]")

        # 寿元
        lifespan_pct = s.age / s.max_lifespan * 100 if s.max_lifespan > 0 else 0
        ls_color = "green" if lifespan_pct < 50 else ("yellow" if lifespan_pct < 80 else "red")
        grid.add_row(f"寿元  ⏳ [{ls_color}]{s.lifespan_remaining:.1f}[/] 年  (年龄 {s.age:.1f})")

        # 灵石
        grid.add_row(f"灵石  💎 [yellow]{s.spirit_stones}[/]")

        # Buffs
        if s.buffs:
            buff_text = "  ".join(f"[green]{b.name}[/]" for b in s.buffs)
            grid.add_row(f"[bold]状态[/]  {buff_text}")

        # 限时事件
        if s.timed_events:
            for key, remain in s.timed_events.items():
                if key == "secret_realm":
                    grid.add_row(f"[yellow]⚡ 秘境开启（{remain}次）[/]")

        # 因果链提示
        if s.pending_chain_event:
            hints = {
                "herb_found": "💡 灵草待处理 → 探索",
                "beast_attack": "💡 妖兽踪迹 → 探索追踪",
            }
            hint = hints.get(s.pending_chain_event, "")
            if hint:
                grid.add_row(f"[yellow]{hint}[/]")

        panel = Panel(grid, title="🧘 角色状态", border_style="green")
        self.update(panel)


class LogPanel(RichLog):
    """事件日志面板：滚动显示游戏事件"""

    def __init__(self, **kwargs):
        super().__init__(highlight=True, markup=True, wrap=True, **kwargs)
        self.max_lines = 1000

    def on_mount(self) -> None:
        self.write("[dim]┈ 修仙之路，由此开始 ┈[/]")
        self.write("")

    def add_log(self, message: str) -> None:
        """添加一条日志"""
        self.write(message)

    def add_logs(self, messages: list[str]) -> None:
        """批量添加日志"""
        for msg in messages:
            self.write(msg)

    def clear_log(self) -> None:
        self.clear()


class ActionButton(Button):
    """操作按钮，绑定键盘快捷键"""

    ALLOW_SELECT = False

    def __init__(self, label: str, action_id: str, shortcut: str, **kwargs):
        display = f"{shortcut.upper()}. {label}"
        super().__init__(display, id=action_id, **kwargs)
        self.shortcut = shortcut.lower()
        self.action_id = action_id


class ActionMenu(Widget):
    """操作菜单面板，包含所有可执行操作按钮"""

    def compose(self):
        with Vertical():
            yield ActionButton("修炼", "cultivate", "c")
            yield ActionButton("探索", "explore", "e")
            yield ActionButton("休息", "rest", "r")
            yield ActionButton("炼丹", "refine_pill", "d")
            yield ActionButton("坊市", "market", "m")
            yield ActionButton("批量闭关", "batch", "b")
            yield ActionButton("突  破", "breakthrough", "t")
            yield ActionButton("秘境探索", "secret_realm", "p")
            yield ActionButton("存  档", "save", "s")

    def on_mount(self) -> None:
        self.styles.width = 22

    def set_enabled(self, action_id: str, enabled: bool) -> None:
        """启用/禁用某个按钮"""
        for child in self.query(ActionButton):
            if child.action_id == action_id:
                child.disabled = not enabled


class MessageBar(Static):
    """底部消息栏，显示当前操作反馈"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._message = "[dim]欢迎来到修仙世界！选择操作开始你的修行之路。[/]"

    def on_mount(self) -> None:
        self.update(self._message)

    def show_message(self, message: str) -> None:
        """显示一条消息"""
        self._message = message
        self.update(message)
        # 自动清除（Textual 中通过 set_timer）
        self.set_timer(5.0, self._clear_message)

    def _clear_message(self) -> None:
        self._message = "[dim]选择操作继续你的修行之路...[/]"
        self.update(self._message)


class ChroniclePanel(Static):
    """修仙年表面板（用于游戏结束或查看）"""

    def __init__(self, chronicle: list, **kwargs):
        super().__init__(**kwargs)
        self.chronicle = chronicle

    def on_mount(self) -> None:
        self._render()

    def _render(self) -> None:
        lines = ["[bold yellow]📜 修仙年表[/]", ""]
        if not self.chronicle:
            lines.append("[dim]尚无记录...[/]")
        else:
            for entry in self.chronicle:
                lines.append(f"  第 {entry.year:.1f} 年 → {entry.text}")
        self.update("\n".join(lines))


# ─── 进度条辅助 ──────────────────────────────────────

def _health_bar(ratio: float, length: int = 20) -> str:
    """气血进度条（红色系）"""
    filled = int(ratio * length)
    if ratio > 0.5:
        color = "green"
    elif ratio > 0.2:
        color = "yellow"
    else:
        color = "red"
    bar = "█" * filled + "░" * (length - filled)
    return f"[{color}]{bar}[/]"


def _qi_bar(ratio: float, length: int = 20) -> str:
    """灵气进度条（蓝色系）"""
    filled = int(ratio * length)
    if ratio > 0.5:
        color = "cyan"
    elif ratio > 0.2:
        color = "blue"
    else:
        color = "dim blue"
    bar = "█" * filled + "░" * (length - filled)
    return f"[{color}]{bar}[/]"
