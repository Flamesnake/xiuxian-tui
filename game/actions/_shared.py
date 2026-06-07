"""
共享内部工具函数。
"""

from __future__ import annotations

import random

from game.state import PlayerState


def advance_time(state: PlayerState, years: float, rng: random.Random) -> list[str]:
    """推进时间，更新 buff，处理限时事件过期"""
    msgs = []
    state.age += years

    expired = state.tick_buffs()
    for name in expired:
        msgs.append(f"[dim]状态 [{name}] 已消失。[/]")

    expired_events = []
    for key, remaining in list(state.timed_events.items()):
        state.timed_events[key] = remaining - 1
        if state.timed_events[key] <= 0:
            expired_events.append(key)
            del state.timed_events[key]
    if "secret_realm" in expired_events:
        msgs.append("[yellow]秘境通道已关闭，错失了一次机缘。[/]")

    return msgs


def clamp_state(state: PlayerState) -> None:
    """确保属性在合理范围内"""
    state.hp = max(0, min(state.hp, state.max_hp))
    state.qi = max(0, min(state.qi, state.max_qi))
    state.spirit_stones = max(0, state.spirit_stones)
    state.cultivation = max(0, state.cultivation)
