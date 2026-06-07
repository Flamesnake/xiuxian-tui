"""
自定义 Textual 组件：状态面板、日志面板、主面板、状态栏
"""

from __future__ import annotations

from enum import Enum, auto

from rich.panel import Panel
from rich.table import Table
from textual.widgets import RichLog, Static

from game.config import TRIBULATION_CONFIG
from game.state import PlayerState, num_to_cn


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
        grid.add_row(f"寿元  ⌛ [{ls_color}]{s.lifespan_remaining:.1f}[/] 年  (年龄 {s.age:.1f})")

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
    """事件日志面板：滚动显示重要游戏事件"""

    # 来自自动挂机的消息只有包含以下关键词才写入历史日志
    IMPORTANT_KEYWORDS = {"天劫", "突破", "秘境", "✦", "恭喜", "死亡", "道陨", "雷劫"}

    def __init__(self, **kwargs):
        super().__init__(highlight=True, markup=True, wrap=True, **kwargs)
        self.max_lines = 500

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

    def add_filtered_log(self, messages: list[str], from_auto: bool = False) -> None:
        """智能添加日志：自动过滤挂机刷屏"""
        for msg in messages:
            if not from_auto or any(kw in msg for kw in self.IMPORTANT_KEYWORDS):
                self.write(msg)

    def clear_log(self) -> None:
        self.clear()


# ─── PanelView ────────────────────────────────────


class PanelView(Enum):
    """主信息面板视图枚举"""
    IDLE = auto()
    EXPLORE = auto()
    BREAKTHROUGH = auto()
    MARKET = auto()
    REFINE = auto()
    SECRET_REALM = auto()
    HELP = auto()        # /help 命令列表
    PLACEHOLDER = auto()  # 功能开发中


# ─── 视图命令权限 ────────────────────────────────

# 每个视图只能执行本视图的关键命令
VIEW_COMMANDS: dict[PanelView, list[str]] = {
    PanelView.IDLE: [
        "explore", "breakthrough", "market", "refine", "secret", "buy",
        "storage", "sect", "relationship", "settings",
    ],
    PanelView.EXPLORE: ["explore"],
    PanelView.BREAKTHROUGH: ["breakthrough"],
    PanelView.MARKET: ["buy"],
    PanelView.REFINE: ["refine"],
    PanelView.SECRET_REALM: ["secret"],
    PanelView.HELP: [],
    PanelView.PLACEHOLDER: [],
}

# 通用命令（任何视图均可使用）
UNIVERSAL_COMMANDS = ["auto", "save", "help", "cls", "back", "logout"]

CMD_LABELS: dict[str, str] = {
    "explore": "探索", "breakthrough": "突破", "market": "坊市",
    "refine": "炼丹", "secret": "秘境", "buy": "购买",
    "save": "存档", "storage": "储物戒", "sect": "宗门",
    "relationship": "人物", "settings": "设置", "auto": "挂机",
    "help": "帮助", "cls": "清屏", "back": "返回", "logout": "登出",
}


def format_cmd_hints(view: PanelView) -> str:
    """生成当前视图的可用命令提示"""
    cmds = list(VIEW_COMMANDS.get(view, []))
    all_cmds = cmds + [c for c in UNIVERSAL_COMMANDS if c not in cmds]
    parts = [f"[cyan]/{c}[/]" for c in all_cmds]
    return f"[dim]命令: {'  '.join(parts)}[/]"


# ─── MainPanel ────────────────────────────────────


class MainPanel(Static):
    """主信息面板：右上核心交互区，多视图切换"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._view = PanelView.IDLE
        self._data: dict = {}
        self._state: PlayerState | None = None

    def set_state(self, state: PlayerState) -> None:
        """保存最新 state 引用，刷新 IDLE 视图时使用"""
        self._state = state

    def set_view(self, view: PanelView, data: dict | None = None) -> None:
        """切换视图并立即渲染"""
        self._view = view
        if data:
            self._data.update(data)
        self._refresh_view()

    def _refresh_view(self) -> None:
        if self._view == PanelView.IDLE:
            self._render_idle()
        elif self._view == PanelView.EXPLORE:
            self._render_explore()
        elif self._view == PanelView.BREAKTHROUGH:
            self._render_breakthrough()
        elif self._view == PanelView.MARKET:
            self._render_market()
        elif self._view == PanelView.REFINE:
            self._render_refine()
        elif self._view == PanelView.SECRET_REALM:
            self._render_secret_realm()
        elif self._view == PanelView.HELP:
            self._render_help()
        else:
            self._render_placeholder()

    # ─── IDLE ─────────────────────────────────────

    def _render_idle(self) -> None:
        s = self._state
        if not s:
            self.update(Panel("", title="📊 修仙统计", border_style="blue"))
            return

        grid = Table.grid(padding=(0, 2), expand=True)
        grid.add_column(justify="left", ratio=1)

        grid.add_row(f"境界: [bold yellow]{s.realm_name}{num_to_cn(s.layer)}层[/]    "
                     f"年龄: {s.age:.1f}年    灵石: [yellow]{s.spirit_stones}[/]")

        grid.add_row("")
        progress = s.cultivation_progress
        bar_len = 30
        filled = int(progress * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        grid.add_row(f"修为: [green]{bar}[/] {progress*100:.0f}%")
        grid.add_row(f"     [dim]{s.cultivation} / {s.cultivation_max}[/]")

        grid.add_row("")
        tips = []
        if s.cultivation >= s.cultivation_max:
            tips.append("⚡ [yellow]修为已满！输入 /breakthrough 尝试突破[/]")
        if s.hp < s.max_hp * 0.3:
            tips.append("🩹 [red]气血过低，挂机将自动休息[/]")
        if s.timed_events:
            if "secret_realm" in s.timed_events:
                tips.append("🏯 [yellow]秘境已开启！输入 /secret 前往探索[/]")
        if s.pending_chain_event:
            tips.append("🔍 [yellow]有未处理的事件，输入 /explore 探索[/]")
        if not tips:
            tips.append("💡 [dim]挂机修炼中，输入 /explore 探索或 /breakthrough 突破[/]")

        for tip in tips:
            grid.add_row(tip)

        # 命令提示
        grid.add_row("")
        grid.add_row(format_cmd_hints(self._view))

        self.update(Panel(grid, title="📊 修仙统计", border_style="blue"))

    # ─── EXPLORE ──────────────────────────────────

    def _render_explore(self) -> None:
        lines = self._data.get("messages", [])
        event_name = self._data.get("event_name", "探索")

        grid = Table.grid(padding=(0, 1), expand=True)
        grid.add_column(justify="left", ratio=1)

        for msg in lines[:8]:
            grid.add_row(msg)

        grid.add_row("")
        grid.add_row("[dim]/explore 继续探索  |  /back 返回修仙统计[/]")

        # 命令提示
        grid.add_row("")
        grid.add_row(format_cmd_hints(self._view))

        self.update(Panel(grid, title=f"🔍 {event_name}", border_style="cyan"))

    # ─── BREAKTHROUGH ─────────────────────────────

    def _render_breakthrough(self) -> None:
        s = self._state
        if s is None:
            self.update(Panel("[red]状态不可用[/]", title="⚡ 突破", border_style="yellow"))
            return
        from game.config import REALMS
        realm = REALMS[s.realm_idx]

        grid = Table.grid(padding=(0, 1), expand=True)
        grid.add_column(justify="left", ratio=1)

        if s.layer >= realm.max_layer and s.realm_idx < len(REALMS) - 1:
            target = REALMS[s.realm_idx + 1]
            grid.add_row("[yellow]═══ 突破大境界 ═══[/]")
            grid.add_row(f"{s.realm_name}{num_to_cn(s.layer)}层 → [bold]{target.name}[/]")
            grid.add_row(f"蕴含天劫，需连续抵挡 {TRIBULATION_CONFIG['strikes']} 道雷劫。")
        else:
            grid.add_row("[yellow]═══ 小层突破 ═══[/]")
            grid.add_row(f"{s.realm_name}{num_to_cn(s.layer)}层 → {num_to_cn(s.layer + 1)}层")

        needed = s.cultivation_max
        if s.cultivation >= needed:
            grid.add_row("")
            grid.add_row("[green]✓ 修为已满，可以突破[/]")
            rate = realm.breakthrough_base
            if s.hp < s.max_hp * 0.3:
                rate -= 0.2
            grid.add_row(f"成功率: [yellow]{rate*100:.0f}%[/]")
            grid.add_row("")
            grid.add_row("[dim]/breakthrough 尝试突破  |  /back 返回[/]")
        else:
            grid.add_row("")
            grid.add_row(f"[red]修为不足 ({s.cultivation}/{needed})[/]")
            grid.add_row("[dim]继续挂机修炼...[/]")

        # 命令提示
        grid.add_row("")
        grid.add_row(format_cmd_hints(self._view))

        self.update(Panel(grid, title="⚡ 突破", border_style="yellow"))

    # ─── MARKET ───────────────────────────────────

    def _render_market(self) -> None:
        from game.config import PILLS

        grid = Table.grid(padding=(0, 1), expand=True)
        grid.add_column(justify="left", ratio=1)

        grid.add_row("[yellow]━━━ 坊市 ━━━[/]")
        grid.add_row("")

        for name, info in PILLS.items():
            grid.add_row(f"[bold]{name}[/]  💎 {info['cost']} 灵石")
            grid.add_row(f"  [dim]{info['desc']}[/]")
            grid.add_row("")

        grid.add_row("[dim]/buy <丹药名> 购买  |  /back 返回[/]")

        # 命令提示
        grid.add_row("")
        grid.add_row(format_cmd_hints(self._view))

        self.update(Panel(grid, title="🏪 坊市", border_style="yellow"))

    # ─── REFINE ───────────────────────────────────

    def _render_refine(self) -> None:
        messages = self._data.get("messages", ["[dim]炼丹结束。[/]"])
        grid = Table.grid(padding=(0, 1), expand=True)
        grid.add_column(justify="left", ratio=1)
        for msg in messages[:6]:
            grid.add_row(msg)

        # 命令提示
        grid.add_row("")
        grid.add_row("[dim]/refine 继续炼丹  |  /back 返回[/]")
        grid.add_row("")
        grid.add_row(format_cmd_hints(self._view))

        self.update(Panel(grid, title="🔥 炼丹", border_style="magenta"))

    # ─── SECRET REALM ─────────────────────────────

    def _render_secret_realm(self) -> None:
        messages = self._data.get("messages", ["秘境探索结束。"])
        grid = Table.grid(padding=(0, 1), expand=True)
        grid.add_column(justify="left", ratio=1)
        for msg in messages[:6]:
            grid.add_row(msg)

        # 命令提示
        grid.add_row("")
        grid.add_row("[dim]/secret 继续探索秘境  |  /back 返回[/]")
        grid.add_row("")
        grid.add_row(format_cmd_hints(self._view))

        self.update(Panel(grid, title="🏯 秘境", border_style="magenta"))

    # ─── HELP ────────────────────────────────────

    def _render_help(self) -> None:
        lines = self._data.get("lines", ["[bold]帮助信息[/]"])

        grid = Table.grid(padding=(0, 1), expand=True)
        grid.add_column(justify="left", ratio=1)

        for line in lines:
            if line.strip() == "":
                grid.add_row("")
            else:
                grid.add_row(line)

        # 命令提示
        grid.add_row("")
        grid.add_row(format_cmd_hints(self._view))

        self.update(Panel(grid, title="📖 帮助", border_style="cyan"))

    # ─── PLACEHOLDER ──────────────────────────────

    def _render_placeholder(self) -> None:
        title = self._data.get("title", "功能")
        desc = self._data.get("description", "功能开发中，敬请期待...")

        grid = Table.grid(padding=(0, 1), expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_row("")
        grid.add_row("")
        grid.add_row("[yellow]🏗 功能开发中...[/]")
        grid.add_row("")
        grid.add_row(f"[bold]{title}[/]")
        grid.add_row("")
        grid.add_row(f"[dim]{desc}[/]")

        # 命令提示
        grid.add_row("")
        grid.add_row("")
        grid.add_row(format_cmd_hints(self._view))

        self.update(Panel(grid, title=f"🔮 {title}", border_style="blue"))


# ─── StatusBar ────────────────────────────────────


class StatusBar(Static):
    """底部状态栏：显示挂机状态、实时数值变化"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._text = "[dim]欢迎来到修仙世界[/]"

    def on_mount(self) -> None:
        self.update(self._text)

    def update_status(self, text: str) -> None:
        """更新状态栏文本"""
        self._text = text
        self.update(text)

    def refresh_message(self, text: str) -> None:
        """显示一条临时消息（5秒后恢复挂机状态）"""
        self._text = text
        self.update(text)
        self.set_timer(5.0, self._restore)

    def _restore(self) -> None:
        self.update(self._text)


# ─── 历史记录面板 ──────────────────────────────


class ChroniclePanel(Static):
    """修仙年表面板（用于游戏结束或查看）"""

    def __init__(self, chronicle: list, **kwargs):
        super().__init__(**kwargs)
        self.chronicle = chronicle

    def on_mount(self) -> None:
        self._render_chronicle()

    def _render_chronicle(self) -> None:
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
