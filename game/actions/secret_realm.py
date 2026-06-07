"""
秘境探索（限时事件）。
"""

from __future__ import annotations

import random

from game.actions._shared import clamp_state
from game.config import TIMED_EVENTS_CONFIG
from game.state import PlayerState


def action_enter_secret_realm(state: PlayerState, rng: random.Random) -> tuple[PlayerState, list[str]]:
    """进入秘境（限时事件）"""
    msgs = []
    if "secret_realm" not in state.timed_events:
        msgs.append("[red]附近没有开启的秘境。[/]")
        return state, msgs

    del state.timed_events["secret_realm"]
    te = TIMED_EVENTS_CONFIG["secret_realm"]

    msgs.append("[yellow]══ 进入秘境 ══[/]")
    msgs.append(f"[yellow]{te.description}[/]")

    for attr, val in te.effects.items():
        current = getattr(state, attr, 0)
        setattr(state, attr, current + val)
        if attr == "cultivation":
            msgs.append(f"[green]修为 +{val}[/]")
        elif attr == "spirit_stones":
            msgs.append(f"[green]灵石 +{val}[/]")
        elif attr == "hp":
            msgs.append(f"[red]气血 {val}[/]")

    if rng.random() < 0.3:
        bonus = rng.randint(10, 25)
        state.cultivation += bonus
        msgs.append(f"[yellow]你在秘境深处发现上古功法残篇！修为额外 +{bonus}！[/]")

    msgs.append("[green]秘境探索结束，你满载而归。[/]")
    clamp_state(state)
    return state, msgs
