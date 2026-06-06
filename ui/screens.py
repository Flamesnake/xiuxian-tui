"""
Textual 屏幕：标题画面、主游戏画面、游戏结束画面
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Static, Button, RichLog,
)
from textual.containers import Horizontal, Vertical, Grid, Container
from textual.binding import Binding

from game.config import PLAYER_INIT
from game.state import PlayerState
from game.actions import (
    action_cultivate, action_explore, action_rest,
    action_refine_pill, action_market, action_breakthrough,
    action_batch_cultivate, action_enter_secret_realm,
)
from game.save import save_game, load_game, has_save
from game.state import num_to_cn
from ui.widgets import (
    StatusPanel, LogPanel, ActionMenu, MessageBar,
)

if TYPE_CHECKING:
    pass


# 屏蔽不需要的按键警告
import warnings
warnings.filterwarnings("ignore", message=".*unknown binding.*")


class TitleScreen(Screen):
    """标题画面"""

    BINDINGS = [
        Binding("enter", "start_game", "开始"),
        Binding("escape", "quit", "退出"),
    ]

    TITLE_ART = r"""
[bright_yellow]
    ╔═══════════════════════════════════════════╗
    ║                                           ║
    ║     🌀  修  仙  模  拟  器  🌀            ║
    ║                                           ║
    ║        Cultivation Simulator               ║
    ║                                           ║
    ╚═══════════════════════════════════════════╝
[/]

[dim]  天地为炉，造化为工。阴阳为炭，万物为铜。[/]

"""

    def compose(self) -> ComposeResult:
        yield Container(
            Static(self.TITLE_ART, id="title-art"),
            Button("🌟 开始新游戏", id="new_game", variant="primary"),
            Button("📂 继续游戏", id="continue_game", variant="default"),
            Button("❌ 退出", id="quit_game", variant="default"),
            id="title-container",
        )

    def on_mount(self) -> None:
        # 如果无存档，禁用继续游戏按钮
        if not has_save():
            btn = self.query_one("#continue_game", Button)
            btn.disabled = True
            btn.label = "📂 继续游戏 (无存档)"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new_game":
            self.action_start_game()
        elif event.button.id == "continue_game":
            self.action_continue_game()
        elif event.button.id == "quit_game":
            self.app.exit()

    def action_start_game(self) -> None:
        """开始新游戏"""
        rng = random.Random()
        state = PlayerState(name="无名散修", seed=rng.randint(0, 2**31))
        state.add_chronicle("踏上修仙之路")
        self.app.push_screen(GameScreen(state))

    def action_continue_game(self) -> None:
        """继续游戏"""
        state = load_game()
        if state:
            self.app.push_screen(GameScreen(state))
        else:
            self.query_one("#continue_game", Button).disabled = True
            self.query_one("#continue_game", Button).label = "📂 继续游戏 (读档失败)"

    def action_quit(self) -> None:
        self.app.exit()


class GameScreen(Screen):
    """主游戏界面"""

    BINDINGS = [
        Binding("c", "action_cultivate", "修炼"),
        Binding("e", "action_explore", "探索"),
        Binding("r", "action_rest", "休息"),
        Binding("d", "action_refine_pill", "炼丹"),
        Binding("m", "action_market", "坊市"),
        Binding("b", "action_batch", "批量闭关"),
        Binding("t", "action_breakthrough", "突破"),
        Binding("p", "action_secret_realm", "秘境"),
        Binding("s", "action_save", "存档"),
        Binding("escape", "action_quit_game", "退出"),
    ]

    def __init__(self, state: PlayerState):
        super().__init__()
        self.state = state
        self.rng = random.Random(state.seed if state.seed else 0)

    def compose(self) -> ComposeResult:
        with Grid(id="main-grid"):
            # 左列：状态面板
            with Vertical(id="left-panel"):
                yield StatusPanel(self.state, id="status")
            # 中列：日志面板
            with Vertical(id="center-panel"):
                yield LogPanel(id="log")
            # 右列：操作菜单
            with Vertical(id="right-panel"):
                yield ActionMenu(id="actions")
        # 底部消息
        yield MessageBar(id="message")

    def on_mount(self) -> None:
        self._setup_grid()
        self._focus_screen()
        # 初始欢迎消息
        log = self.query_one("#log", LogPanel)
        log.add_log(f"[yellow]━━━ 修仙之路 ━━━[/]")
        log.add_log(f"[green]你，{self.state.name}，一名不起眼的散修。[/]")
        log.add_log(f"[green]天地广阔，你的修仙之路从今日开始。[/]")
        log.add_log("")
        self._update_message("按对应快捷键操作，或点击右侧按钮。")

    def _focus_screen(self) -> None:
        """确保屏幕捕获键盘事件"""
        self.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理操作按钮点击事件"""
        button_id = event.button.id
        action_map = {
            "cultivate": self.action_cultivate,
            "explore": self.action_explore,
            "rest": self.action_rest,
            "refine_pill": self.action_refine_pill,
            "market": self.action_market,
            "batch": self.action_batch,
            "breakthrough": self.action_breakthrough,
            "secret_realm": self.action_secret_realm,
            "save": self.action_save,
        }
        handler = action_map.get(button_id)
        if handler:
            handler()
            # 点击按钮后确保屏幕仍然捕获键盘
            self._focus_screen()

    def _setup_grid(self) -> None:
        """设置网格布局"""
        grid = self.query_one("#main-grid", Grid)
        grid.styles.grid_size_columns = 3
        grid.styles.grid_size_rows = 1
        grid.styles.grid_gutter_horizontal = 1
        grid.styles.width = "100%"
        grid.styles.height = "100%"

        self.query_one("#left-panel").styles.width = 30
        self.query_one("#center-panel").styles.width = "1fr"
        self.query_one("#right-panel").styles.width = 22

    def _update_state_ui(self) -> None:
        """刷新所有 UI 组件反映最新状态"""
        # 更新状态面板
        status = self.query_one("#status", StatusPanel)
        status.refresh_state(self.state)

        # 检查是否死亡
        if self.state.is_dead:
            self._game_over()

    def _update_message(self, msg: str) -> None:
        """更新底部消息栏"""
        msg_bar = self.query_one("#message", MessageBar)
        msg_bar.show_message(msg)

    def _add_logs(self, messages: list[str]) -> None:
        """添加日志"""
        log = self.query_one("#log", LogPanel)
        log.add_logs(messages)

    def _check_breakthrough(self) -> bool:
        """检查是否可突破，自动提示"""
        needed = self.state.cultivation_max
        if self.state.cultivation >= needed and self.state.hp > 0:
            self._add_logs([f"[yellow]⚡ 修为已满！按 [T] 尝试突破至下一层！[/]"])
            self._update_message("修为已满，尝试突破！")
            return True
        return False

    def _auto_save(self) -> None:
        """自动存档"""
        try:
            save_game(self.state)
        except Exception:
            pass  # 存档失败不打断游戏

    def _game_over(self) -> None:
        """游戏结束"""
        self.app.push_screen(GameOverScreen(self.state))

    # ─── 操作处理 ──────────────────────────────────

    def _handle_action(self, action_fn, success_msg: str = "") -> None:
        """通用操作处理模板"""
        msgs = []
        try:
            result = action_fn(self.state, self.rng)
            if len(result) == 3:
                # (state, msgs, ...)
                self.state, action_msgs, *_ = result
            else:
                self.state, action_msgs = result
            msgs.extend(action_msgs)
        except Exception as e:
            msgs.append(f"[red]错误: {e}[/]")

        if msgs:
            self._add_logs(msgs)
            last = msgs[-1] if msgs else success_msg
            self._update_message(last)

        self._auto_save()
        self._update_state_ui()
        self._check_breakthrough()

    def action_cultivate(self) -> None:
        self._handle_action(action_cultivate, "[green]修炼完成。[/]")

    def action_explore(self) -> None:
        self._handle_action(action_explore, "[dim]探索结束。[/]")

    def action_rest(self) -> None:
        self._handle_action(action_rest, "[green]休息完毕，精神焕发。[/]")

    def action_refine_pill(self) -> None:
        self._handle_action(action_refine_pill, "[yellow]炼丹结束。[/]")

    def action_market(self) -> None:
        self._handle_action(action_market, "[green]坊市交易完成。[/]")

    def action_breakthrough(self) -> None:
        msgs = []
        try:
            state, action_msgs, success = action_breakthrough(self.state, self.rng, self.app)
            self.state = state
            msgs.extend(action_msgs)
        except Exception as e:
            msgs.append(f"[red]错误: {e}[/]")

        self._add_logs(msgs)
        if msgs:
            self._update_message(msgs[-1])
        self._auto_save()
        self._update_state_ui()

    def action_batch(self) -> None:
        self._handle_action(
            lambda s, r: action_batch_cultivate(s, r, count=10),
            "[green]批量闭关结束。[/]"
        )

    def action_secret_realm(self) -> None:
        self._handle_action(action_enter_secret_realm, "[yellow]秘境探索结束。[/]")

    def action_save(self) -> None:
        path = save_game(self.state, manual=True)
        self._add_logs([f"[green]✓ 游戏已存档 ({path})[/]"])
        self._update_message(f"已保存到 {path}")

    def action_quit_game(self) -> None:
        save_game(self.state)
        self.app.pop_screen()
        self.app.push_screen(TitleScreen())


class GameOverScreen(Screen):
    """游戏结束画面"""

    BINDINGS = [
        Binding("enter", "restart", "重新开始"),
        Binding("escape", "quit", "退出"),
    ]

    def __init__(self, state: PlayerState):
        super().__init__()
        self.state = state

    def compose(self) -> ComposeResult:
        yield Container(
            Static("", id="gameover-art"),
            Static("", id="gameover-reason"),
            Static("", id="gameover-stats"),
            Static("", id="gameover-chronicle"),
            Button("🔄 重新开始", id="restart", variant="primary"),
            Button("❌ 退出", id="quit", variant="default"),
            id="gameover-container",
        )

    def on_mount(self) -> None:
        s = self.state
        if s.hp <= 0:
            art = "[red]\n    💀 道 陨  💀\n[/]"
            reason = f"[red]你在 {s.realm_name}{num_to_cn(s.layer)}层 时气血耗尽，道途中断...[/]"
        else:
            art = "[yellow]\n    ⌛ 寿 元 已 尽  ⌛\n[/]"
            reason = f"[yellow]你享年 {s.age:.1f} 岁，止步于 {s.realm_name}{num_to_cn(s.layer)}层。[/]"
        stats = (
            f"[dim]最终境界: {s.realm_name}{num_to_cn(s.layer)}层[/]\n"
            f"[dim]最终修为: {s.cultivation}[/]\n"
            f"[dim]总灵石收入: {s.spirit_stones}[/]"
        )

        lines = ["[bold yellow]📜 修仙年表[/]"]
        for entry in s.chronicle:
            lines.append(f"  [dim]第 {entry.year:.1f} 年 →[/] {entry.text}")

        self.query_one("#gameover-art", Static).update(art)
        self.query_one("#gameover-reason", Static).update(reason)
        self.query_one("#gameover-stats", Static).update(stats)
        self.query_one("#gameover-chronicle", Static).update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "restart":
            self.action_restart()
        else:
            self.app.exit()

    def action_restart(self) -> None:
        self.app.pop_screen()
        self.app.push_screen(TitleScreen())

    def action_quit(self) -> None:
        self.app.exit()

