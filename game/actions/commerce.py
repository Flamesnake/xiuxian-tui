"""
坊市、炼丹、购买丹药。
"""

from __future__ import annotations

import random

from game.actions._shared import advance_time, clamp_state
from game.config import ACTION_TIME, PILLS
from game.state import PlayerState


def action_refine_pill(state: PlayerState, rng: random.Random) -> tuple[PlayerState, list[str]]:
    """炼丹：消耗灵石 → 获得丹药"""
    msgs = []

    cost = PILLS["聚气丹"]["cost"]
    if state.spirit_stones < cost:
        msgs.append("[red]灵石不足，无法购买炼丹材料。[/]")
        return state, msgs

    state.spirit_stones -= cost

    success = rng.random() < 0.75
    if success:
        effects = PILLS["聚气丹"]["effects"]
        msgs.append(f"[green]你成功炼制了聚气丹！消耗 {cost} 灵石。[/]")

        gained_cultivation = rng.randint(10, 20) + effects.get("cultivation", 0)
        gained_qi = effects.get("qi", 0)

        state.cultivation += gained_cultivation
        msgs.append(f"[green]修为 +{gained_cultivation}[/]")
        if gained_qi:
            state.qi = min(state.max_qi, state.qi + gained_qi)
            msgs.append(f"[green]灵气 +{gained_qi}[/]")
    else:
        msgs.append(f"[red]炼丹失败，{cost} 灵石打了水漂...[/]")

    time_msgs = advance_time(state, ACTION_TIME["refine_pill"], rng)
    msgs.extend(time_msgs)
    clamp_state(state)

    return state, msgs


def action_market(state: PlayerState, rng: random.Random) -> tuple[PlayerState, list[str]]:
    """坊市：买卖物品"""
    msgs = []

    base_income = (state.realm_idx + 1) * 5 + rng.randint(1, 8)

    if rng.random() < 0.4:
        discount = rng.randint(1, 3)
        actual_income = base_income + discount
        msgs.append(f"[green]你在坊市卖出一些杂物和草药，获得 {actual_income} 灵石。[/]")
        msgs.append("[yellow]偶遇打折丹药，顺手买了些补充。[/]")
        state.qi = min(state.max_qi, state.qi + rng.randint(3, 6))
    else:
        msgs.append(f"[green]你在坊市卖出收集的材料，获得 {base_income} 灵石。[/]")

    state.spirit_stones += base_income

    time_msgs = advance_time(state, ACTION_TIME["market"], rng)
    msgs.extend(time_msgs)
    clamp_state(state)

    return state, msgs


def action_buy_pill(state: PlayerState, rng: random.Random, pill_name: str) -> tuple[PlayerState, list[str]]:
    """在坊市购买指定丹药"""
    msgs = []
    pill = PILLS.get(pill_name)
    if not pill:
        msgs.append("[red]没有这种丹药。[/]")
        return state, msgs

    if state.spirit_stones < pill["cost"]:
        msgs.append(f"[red]灵石不足！{pill_name} 需要 {pill['cost']} 灵石。[/]")
        return state, msgs

    state.spirit_stones -= pill["cost"]
    effects = pill["effects"]

    msgs.append(f"[green]你购买了 {pill_name}，消耗 {pill['cost']} 灵石。[/]")
    if "hp" in effects:
        state.hp = min(state.max_hp, state.hp + effects["hp"])
        msgs.append(f"[green]气血 +{effects['hp']}[/]")
    if "qi" in effects:
        state.qi = min(state.max_qi, state.qi + effects["qi"])
        msgs.append(f"[green]灵气 +{effects['qi']}[/]")
    if "cultivation" in effects:
        state.cultivation += effects["cultivation"]
        msgs.append(f"[green]修为 +{effects['cultivation']}[/]")
    if "breakthrough_protect" in effects:
        state.breakthrough_protected = True
        msgs.append("[yellow]护脉丹已生效，下次突破失败反噬减轻。[/]")

    clamp_state(state)
    return state, msgs
