"""
探索 + 随机事件触发 + 因果链/限时事件。

同时包含 game/events.py 中的辅助函数，统一管理事件查询逻辑。
"""

from __future__ import annotations

import random

from game.actions._shared import advance_time, clamp_state
from game.config import (
    ACTION_TIME,
    TIMED_EVENTS_CONFIG,
    pick_chain_event,
    pick_event,
)
from game.state import PlayerState


def action_explore(state: PlayerState, rng: random.Random) -> tuple[PlayerState, list[str]]:
    """探索：消耗时间 → 触发随机事件"""
    msgs = []

    # 先检查是否有未处理的因果链
    if state.pending_chain_event:
        chain_key = state.pending_chain_event
        chain_event = pick_chain_event(chain_key, rng)
        state.pending_chain_event = None
        if chain_event:
            msgs.append(f"[{chain_event.color}]{chain_event.description}[/]")
            for attr, val in chain_event.effects.items():
                setattr(state, attr, getattr(state, attr, 0) + val)
            if "cultivation" in chain_event.effects:
                msgs.append(f"[green]修为 +{chain_event.effects['cultivation']}[/]")
            if "hp" in chain_event.effects:
                v = chain_event.effects["hp"]
                msgs.append(f"[{'red' if v<0 else 'green'}]{'气血 -' if v<0 else '气血 +'}{abs(v)}[/]")
            if "spirit_stones" in chain_event.effects:
                v = chain_event.effects["spirit_stones"]
                msgs.append(f"[{'red' if v<0 else 'green'}]{'灵石 -' if v<0 else '灵石 +'}{abs(v)}[/]")
        clamp_state(state)
        time_msgs = advance_time(state, ACTION_TIME["explore"], rng)
        msgs.extend(time_msgs)
        return state, msgs

    # 检查限时事件
    if "secret_realm" in state.timed_events:
        msgs.append("[yellow]⚡ 秘境入口仍在开启中！进入探索可获得大机缘！[/]")

    # 随机事件
    event = pick_event(state.realm_idx, rng)
    if event:
        msgs.append(f"[{event.color}]── {event.title} ──[/]")
        msgs.append(f"[{event.color}]{event.description}[/]")
        for attr, val in event.effects.items():
            old = getattr(state, attr, 0)
            setattr(state, attr, old + val)
            if attr == "cultivation" and val != 0:
                msgs.append(f"[green]修为 {'+' if val>0 else ''}{val}[/]")
            elif attr == "hp" and val != 0:
                msgs.append(f"[{'red' if val<0 else 'green'}]{'气血 -' if val<0 else '气血 +'}{abs(val)}[/]")
            elif attr == "spirit_stones" and val != 0:
                msgs.append(f"[{'red' if val<0 else 'green'}]{'灵石 -' if val<0 else '灵石 +'}{abs(val)}[/]")
            elif attr == "qi" and val != 0:
                msgs.append(f"[{'red' if val<0 else 'cyan'}]{'灵气 -' if val<0 else '灵气 +'}{abs(val)}[/]")

        # 检查是否触发因果链
        if event.tags:
            if "herb" in event.tags and "positive" in event.tags:
                if rng.random() < 0.5:
                    state.pending_chain_event = "herb_found"
                    msgs.append("[yellow]💡 你可以选择移植灵草或将其出售。继续探索以决定。[/]")
            if "beast" in event.tags and "combat" in event.tags:
                if rng.random() < 0.4:
                    state.pending_chain_event = "beast_attack"
                    msgs.append("[yellow]💡 你发现妖兽踪迹，可追踪其巢穴。继续探索以追踪。[/]")

        # 检查是否触发限时事件
        if "special" in event.tags and rng.random() < 0.15:
            te = TIMED_EVENTS_CONFIG.get("secret_realm")
            if te:
                state.timed_events["secret_realm"] = te.duration
                msgs.append(f"[yellow]⚡ {te.name}（持续{te.duration}次行动）[/]")
    else:
        msgs.append("[dim]你四处走动，今日风平浪静，无所收获。[/]")

    # 自然恢复少量灵气
    qi_recovery = rng.randint(1, 3)
    state.qi = min(state.max_qi, state.qi + qi_recovery)
    if qi_recovery > 0:
        msgs.append(f"[dim]灵气自然恢复 +{qi_recovery}[/]")

    time_msgs = advance_time(state, ACTION_TIME["explore"], rng)
    msgs.extend(time_msgs)
    clamp_state(state)

    return state, msgs


# ─── 事件查询辅助（来自 game/events.py） ──────────────────

def has_timed_event(state: PlayerState, key: str) -> bool:
    """检查是否有某个限时事件活跃"""
    return key in state.timed_events


def timed_event_description(state: PlayerState, key: str) -> str:
    """获取限时事件的描述文本（用于 UI 显示）"""
    if key in state.timed_events:
        te = TIMED_EVENTS_CONFIG.get(key)
        if te:
            remaining = state.timed_events[key]
            return f"[yellow]⚡ {te.name}（剩余 {remaining} 次行动）[/]"
    return ""


def get_timed_events_info(state: PlayerState) -> list[str]:
    """获取所有活跃限时事件的信息列表"""
    info = []
    for key, remaining in state.timed_events.items():
        te = TIMED_EVENTS_CONFIG.get(key)
        if te:
            info.append(f"⚡ {te.name}（{remaining} 次）")
    return info


def has_pending_chain(state: PlayerState) -> bool:
    """检查是否有待处理的因果链事件"""
    return state.pending_chain_event is not None


def pending_chain_hint(state: PlayerState) -> str:
    """获取因果链提示"""
    hints = {
        "herb_found": "[yellow]💡 继续探索以决定灵草的用途[/]",
        "beast_attack": "[yellow]💡 继续探索以追踪妖兽巢穴[/]",
    }
    return hints.get(state.pending_chain_event or "", "")
