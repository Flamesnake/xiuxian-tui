"""
Textual 屏幕：标题画面、主游戏画面（命令输入模式）、游戏结束画面
"""

from __future__ import annotations

import random
import warnings

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid, Vertical
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Button, Input, Static

from game.actions import (
    action_breakthrough,
    action_buy_pill,
    action_enter_secret_realm,
    action_explore,
    action_market,
    action_refine_pill,
    auto_tick,
)
from game.actions.auto import ACTION_NAMES
from game.save import has_save, load_game, save_game
from game.state import PlayerState, num_to_cn
from ui.widgets import (
    CMD_LABELS,
    VIEW_COMMANDS,
    LogPanel,
    MainPanel,
    PanelView,
    StatusBar,
    StatusPanel,
)

warnings.filterwarnings("ignore", message=".*unknown binding.*")


# ─── 命令注册表 ──────────────────────────────────

COMMANDS: dict[str, tuple[str, str]] = {
    "explore":       ("探索", "探索未知区域，获得灵石和道具"),
    "breakthrough":  ("突破", "尝试突破至下一层/下一境界"),
    "market":        ("坊市", "去坊市交易，赚取灵石"),
    "refine":        ("炼丹", "消耗灵石炼制丹药"),
    "buy":           ("购买", "购买丹药，如 /buy 聚气丹"),
    "secret":        ("秘境", "进入开启中的秘境探索"),
    "save":          ("存档", "保存游戏进度"),
    "storage":       ("储物戒", "打开储物空间（功能开发中）"),
    "sect":          ("宗门", "打开宗门界面（功能开发中）"),
    "relationship":  ("人物", "查看人物关系（功能开发中）"),
    "settings":      ("设置", "游戏设置（功能开发中）"),
    "auto":          ("挂机", "切换挂机模式"),
    "cls":           ("清屏", "清除历史日志"),
    "clear":         ("清屏", "清除历史日志"),
    "help":          ("帮助", "显示本帮助信息"),
    "back":          ("返回", "返回修仙统计主界面"),
    "logout":        ("登出", "返回标题画面"),
}


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
        rng = random.Random()
        state = PlayerState(name="无名散修", seed=rng.randint(0, 2**31))
        state.add_chronicle("踏上修仙之路")
        self.app.push_screen(GameScreen(state))

    def action_continue_game(self) -> None:
        state = load_game()
        if state:
            self.app.push_screen(GameScreen(state))
        else:
            self.query_one("#continue_game", Button).disabled = True
            self.query_one("#continue_game", Button).label = "📂 继续游戏 (读档失败)"

    def action_quit(self) -> None:
        self.app.exit()


class GameScreen(Screen):
    """主游戏界面——命令输入模式"""

    # 仅保留 escape 退出快捷键，所有操作通过 /command 输入
    BINDINGS = [
        Binding("escape", "action_quit_game", "退出"),
    ]

    def __init__(self, state: PlayerState):
        super().__init__()
        self.state = state
        self.rng = random.Random(state.seed if state.seed else 0)
        self.auto_mode = True
        self.auto_timer: Timer | None = None
        self._prev_cultivation = state.cultivation
        self._prev_qi = state.qi

    def compose(self) -> ComposeResult:
        with Grid(id="top-row"):
            with Vertical(id="panel-status"):
                yield StatusPanel(self.state, id="status")
            with Vertical(id="panel-main"):
                yield MainPanel(id="main-panel")
        yield LogPanel(id="log")
        yield Input(id="cmd-input", placeholder="/ 输入命令（/help 查看帮助）")
        yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        # 初始日志
        log = self.query_one("#log", LogPanel)
        log.add_log("[yellow]━━━ 修仙之路 ━━━[/]")
        log.add_log(f"[green]你，{self.state.name}，一名不起眼的散修。[/]")
        log.add_log("[green]天地广阔，你的修仙之路从今日开始。[/]")
        log.add_log("[dim]输入 /help 查看可用命令。[/]")
        log.add_log("")

        # 初始化主面板
        main = self.query_one("#main-panel", MainPanel)
        main.set_state(self.state)
        main.set_view(PanelView.IDLE)

        # 初始化底部状态栏
        self._update_status_bar("⏳ 挂机中")

        # 自动挂机默认开启
        self.auto_mode = True
        self.auto_timer = self.set_interval(0.3, self._auto_tick)

        # 输入框焦点
        self.query_one("#cmd-input", Input).focus()

    # ─── 命令系统 ──────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理输入框提交的命令"""
        raw = event.value.strip()
        self.query_one("#cmd-input", Input).clear()
        if not raw:
            return
        self._process_command(raw)

    def _process_command(self, text: str) -> None:
        """解析并执行命令（支持参数），按视图限制权限"""
        raw = text.lstrip("/").strip()
        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        log = self.query_one("#log", LogPanel)

        # ── 通用命令（任何视图均可使用） ──
        if cmd in ("help",):
            self._show_help()
            return
        elif cmd in ("cls", "clear"):
            log.clear_log()
            return
        elif cmd == "back":
            self.action_back_to_idle()
            return
        elif cmd == "logout":
            self.action_logout()
            return
        elif cmd == "auto":
            self.action_toggle_auto()
            log.add_log(f"[dim]> /{cmd}[/]")
            return
        elif cmd == "save":
            self.action_save()
            log.add_log(f"[dim]> /{cmd}[/]")
            return

        # ── 视图权限检查 ──
        main = self.query_one("#main-panel", MainPanel)
        current_view = main._view
        allowed = VIEW_COMMANDS.get(current_view, [])

        if cmd not in allowed:
            label = CMD_LABELS.get(cmd, cmd)
            log.add_log(f"[red]当前界面不能执行 /{cmd}（{label}）。输入 /help 查看可用命令[/]")
            return

        # ── 带参数命令 ──
        if cmd == "buy":
            if not args:
                log.add_log("[red]用法: /buy <丹药名>   可用丹药：聚气丹、回春丹、蕴神丹、护脉丹[/]")
                return
            log.add_log(f"[dim]> /buy {args}[/]")
            self.action_buy_pill(args)
            return

        # ── 无参数命令 ──
        action_map = {
            "explore": self.action_explore,
            "breakthrough": self.action_breakthrough,
            "market": self.action_market,
            "refine": self.action_refine_pill,
            "secret": self.action_secret_realm,
            "storage": self.action_storage,
            "sect": self.action_sect,
            "relationship": self.action_relationship,
            "settings": self.action_settings,
        }

        if cmd in action_map:
            label = CMD_LABELS.get(cmd, cmd)
            log.add_log(f"[dim]> /{cmd}  — {label}[/]")
            action_map[cmd]()
        else:
            log.add_log(f"[red]未知命令: {text}   输入 /help 查看可用命令[/]")

    def _show_help(self) -> None:
        """在 MainPanel 显示帮助信息"""
        from game.config import PILLS

        lines = ["[bold yellow]📖 可执行命令[/]", ""]

        lines.append("[bold]基础操作:[/]")
        for cmd, (name, desc) in sorted(COMMANDS.items()):
            if cmd in ("clear", "back", "logout", "storage", "sect", "relationship", "settings"):
                continue
            if cmd == "buy":
                lines.append(f"  [cyan]/{cmd} <丹药名>[/]    {desc}")
            else:
                lines.append(f"  [cyan]/{cmd:<16}[/] {desc}")

        lines.append("")
        lines.append("[bold]功能（开发中）:[/]")
        for cmd in ("storage", "sect", "relationship", "settings"):
            name, desc = COMMANDS[cmd]
            lines.append(f"  [cyan]/{cmd:<16}[/] {desc}")

        lines.append("")
        lines.append("[bold]系统:[/]")
        for cmd in ("auto", "save", "back", "logout", "help", "cls"):
            name, desc = COMMANDS[cmd]
            lines.append(f"  [cyan]/{cmd:<16}[/] {desc}")

        lines.append("")
        lines.append("[bold]丹药列表（可购买）:[/]")
        for pill_name, info in PILLS.items():
            lines.append(f"  [green]{pill_name}[/]  💎 {info['cost']}灵石  [dim]{info['desc']}[/]")

        lines.append("")
        lines.append("[bold]购买示例:[/]  [cyan]/buy 聚气丹[/]")

        main = self.query_one("#main-panel", MainPanel)
        main.set_view(PanelView.HELP, {"lines": lines})
        self._update_status_bar("[dim]输入 /<命令> 进行操作  |  /back 返回[/]")

    # ─── 视图导航 ──────────────────────────────────

    def action_back_to_idle(self) -> None:
        """返回修仙统计主界面"""
        main = self.query_one("#main-panel", MainPanel)
        main.set_state(self.state)
        main.set_view(PanelView.IDLE)
        self._update_status_bar("⏳ 回到修仙统计")
        log = self.query_one("#log", LogPanel)
        log.add_log("[dim]> /back  — 返回主界面[/]")

    def action_logout(self) -> None:
        """登出，返回标题画面"""
        save_game(self.state)
        self.app.pop_screen()
        self.app.push_screen(TitleScreen())

    # ─── UI 更新 ──────────────────────────────────

    def _update_status_bar(self, text: str) -> None:
        bar = self.query_one("#status-bar", StatusBar)
        bar.update_status(text)

    def _update_state_ui(self) -> None:
        status = self.query_one("#status", StatusPanel)
        status.refresh_state(self.state)

        main = self.query_one("#main-panel", MainPanel)
        main.set_state(self.state)
        if main._view == PanelView.IDLE:
            main.set_view(PanelView.IDLE)

        if self.state.is_dead:
            self._game_over()

    def _auto_save(self) -> None:
        try:
            save_game(self.state)
        except Exception:
            pass

    def _game_over(self) -> None:
        self.app.push_screen(GameOverScreen(self.state))

    # ─── 自动挂机 ──────────────────────────────────

    def action_toggle_auto(self) -> None:
        if self.auto_timer is not None:
            self.auto_timer.stop()
            self.auto_timer = None
        self.auto_mode = not self.auto_mode
        if self.auto_mode:
            self.auto_timer = self.set_interval(0.3, self._auto_tick)
            self._update_status_bar("⏳ 挂机中")
        else:
            self._update_status_bar("⏸ 挂机已暂停")

    def _auto_tick(self) -> None:
        if self.state.is_dead:
            self.action_toggle_auto()
            return

        prev_cult = self.state.cultivation
        prev_qi = self.state.qi

        new_state, msgs, action = auto_tick(self.state, self.rng)
        self.state = new_state

        if action == "dead":
            self.action_toggle_auto()
            return

        delta_cult = self.state.cultivation - prev_cult
        delta_qi = self.state.qi - prev_qi

        bar_text = "⏳ 挂机中"
        if action == "idle":
            if self.state.cultivation >= self.state.cultivation_max:
                bar_text += "：修为已满，输入 /breakthrough 突破"
            else:
                bar_text += "：等待中..."
        elif action == "cultivate":
            bar_text += f"：修炼  修为 +{delta_cult}"
            if delta_qi < 0:
                bar_text += f"  灵气 {delta_qi}"
        elif action == "rest":
            bar_text += "：休息"
        elif action:
            bar_text += f"：{ACTION_NAMES.get(action, action)}"

        self._update_status_bar(bar_text)

        log = self.query_one("#log", LogPanel)
        log.add_filtered_log(msgs, from_auto=True)

        self._update_state_ui()

    def on_unmount(self) -> None:
        if self.auto_timer is not None:
            self.auto_timer.stop()
            self.auto_timer = None

    # ─── 手动操作 ──────────────────────────────────

    def _handle_action(self, action_fn, panel_view: PanelView = PanelView.IDLE,
                       panel_data: dict | None = None) -> None:
        msgs = []
        try:
            result = action_fn(self.state, self.rng)
            if len(result) == 3:
                self.state, action_msgs, *_ = result
            else:
                self.state, action_msgs = result
            msgs.extend(action_msgs)
        except Exception as e:
            msgs.append(f"[red]错误: {e}[/]")

        if msgs:
            log = self.query_one("#log", LogPanel)
            log.add_logs(msgs)
            self._update_status_bar(msgs[-1])

        if panel_view != PanelView.IDLE:
            main = self.query_one("#main-panel", MainPanel)
            main.set_state(self.state)
            main.set_view(panel_view, panel_data or {"messages": msgs})

        self._auto_save()
        self._update_state_ui()

    def action_explore(self) -> None:
        msgs = []
        try:
            self.state, action_msgs = action_explore(self.state, self.rng)
            msgs.extend(action_msgs)
        except Exception as e:
            msgs.append(f"[red]错误: {e}[/]")

        if msgs:
            log = self.query_one("#log", LogPanel)
            log.add_logs(msgs)
            self._update_status_bar(msgs[-1])

            main = self.query_one("#main-panel", MainPanel)
            main.set_state(self.state)
            main.set_view(PanelView.EXPLORE, {"messages": msgs, "event_name": "探索"})

        self._auto_save()
        self._update_state_ui()

    def action_breakthrough(self) -> None:
        msgs = []
        try:
            state, action_msgs, success = action_breakthrough(self.state, self.rng)
            self.state = state
            msgs.extend(action_msgs)
        except Exception as e:
            msgs.append(f"[red]错误: {e}[/]")

        if msgs:
            log = self.query_one("#log", LogPanel)
            log.add_logs(msgs)
            self._update_status_bar(msgs[-1])

            main = self.query_one("#main-panel", MainPanel)
            main.set_state(self.state)
            main.set_view(PanelView.BREAKTHROUGH)

        self._auto_save()
        self._update_state_ui()

    def action_market(self) -> None:
        msgs = []
        try:
            self.state, action_msgs = action_market(self.state, self.rng)
            msgs.extend(action_msgs)
        except Exception as e:
            msgs.append(f"[red]错误: {e}[/]")

        if msgs:
            log = self.query_one("#log", LogPanel)
            log.add_logs(msgs)
            self._update_status_bar(msgs[-1])

            main = self.query_one("#main-panel", MainPanel)
            main.set_state(self.state)
            main.set_view(PanelView.MARKET)

        self._auto_save()
        self._update_state_ui()

    def action_refine_pill(self) -> None:
        msgs = []
        try:
            self.state, action_msgs = action_refine_pill(self.state, self.rng)
            msgs.extend(action_msgs)
        except Exception as e:
            msgs.append(f"[red]错误: {e}[/]")

        if msgs:
            log = self.query_one("#log", LogPanel)
            log.add_logs(msgs)
            self._update_status_bar(msgs[-1])

            main = self.query_one("#main-panel", MainPanel)
            main.set_state(self.state)
            main.set_view(PanelView.REFINE, {"messages": msgs})

        self._auto_save()
        self._update_state_ui()

    def action_buy_pill(self, pill_name: str) -> None:
        """通过命令购买丹药"""
        msgs = []
        try:
            self.state, action_msgs = action_buy_pill(self.state, self.rng, pill_name)
            msgs.extend(action_msgs)
        except Exception as e:
            msgs.append(f"[red]错误: {e}[/]")

        if msgs:
            log = self.query_one("#log", LogPanel)
            log.add_logs(msgs)
            self._update_status_bar(msgs[-1])

            main = self.query_one("#main-panel", MainPanel)
            main.set_state(self.state)
            main.set_view(PanelView.MARKET)

        self._auto_save()
        self._update_state_ui()

    def action_secret_realm(self) -> None:
        msgs = []
        try:
            self.state, action_msgs = action_enter_secret_realm(self.state, self.rng)
            msgs.extend(action_msgs)
        except Exception as e:
            msgs.append(f"[red]错误: {e}[/]")

        if msgs:
            log = self.query_one("#log", LogPanel)
            log.add_logs(msgs)
            self._update_status_bar(msgs[-1])

            main = self.query_one("#main-panel", MainPanel)
            main.set_state(self.state)
            main.set_view(PanelView.SECRET_REALM, {"messages": msgs})

        self._auto_save()
        self._update_state_ui()

    # ─── 占位功能 ──────────────────────────────────

    def _placeholder(self, title: str, desc: str = "功能开发中，敬请期待...") -> None:
        self._update_status_bar(f"[dim]{title}: {desc}[/]")
        main = self.query_one("#main-panel", MainPanel)
        main.set_view(PanelView.PLACEHOLDER, {"title": title, "description": desc})

    def action_storage(self) -> None:
        self._placeholder("🗄 储物戒", "暂无储物空间\n后续版本将开放装备与物品系统")

    def action_sect(self) -> None:
        self._placeholder("🏛 宗门", "暂无宗门\n后续版本将开放宗门系统")

    def action_relationship(self) -> None:
        self._placeholder("👥 人物关系", "暂无社交关系\n后续版本将开放人物交互")

    def action_settings(self) -> None:
        self._placeholder("⚙ 设置", "游戏设置\n后续版本将开放配置选项")

    # ─── 存档 ──────────────────────────────────────

    def action_save(self) -> None:
        path = save_game(self.state, manual=True)
        self._update_status_bar(f"[green]✓ 已存档 ({path})[/]")

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
