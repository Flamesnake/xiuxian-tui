"""
突破系统：小层突破 + 大境界突破（含天劫）。
"""

from __future__ import annotations

import random

from game.actions._shared import clamp_state
from game.config import REALMS, TRIBULATION_CONFIG, cultivation_needed
from game.state import PlayerState, num_to_cn


def action_breakthrough(state: PlayerState, rng: random.Random) -> tuple[PlayerState, list[str], bool]:
    """
    尝试突破。
    返回 (state, messages, success)
    """
    msgs = []
    realm = REALMS[state.realm_idx]

    needed = state.cultivation_max
    if state.cultivation < needed:
        msgs.append(f"[red]修为不足！({state.cultivation}/{needed})[/]")
        return state, msgs, False

    if state.realm_idx >= len(REALMS) - 1 and state.layer >= realm.max_layer:
        msgs.append("[yellow]你已达修仙界巅峰！举霞飞升指日可待。[/]")
        return state, msgs, False

    if state.layer >= realm.max_layer:
        return _breakthrough_realm(state, rng)
    else:
        return _breakthrough_layer(state, rng)


def _breakthrough_layer(state: PlayerState, rng: random.Random) -> tuple[PlayerState, list[str], bool]:
    """小层突破"""
    msgs = []
    realm = REALMS[state.realm_idx]
    success_rate = realm.breakthrough_base

    if state.hp < state.max_hp * 0.3:
        success_rate -= 0.2
        msgs.append("[red]伤势过重，突破难度增加。[/]")

    roll = rng.random()
    if roll < success_rate:
        state.layer += 1
        state.cultivation = 0
        state.max_lifespan += realm.layer_lifespan_bonus
        msgs.append(f"[yellow]✦ 突破成功！你达到了 {state.title_display}！[/]")
        state.add_chronicle(f"突破至 {state.realm_name}{num_to_cn(state.layer)}层")
    else:
        loss = int(cultivation_needed(state.realm_idx, state.layer + 1)) // 3
        if state.breakthrough_protected:
            loss = loss // 2
            state.breakthrough_protected = False
            msgs.append("[yellow]护脉丹发挥了作用，反噬减轻。[/]")
        state.cultivation = max(0, state.cultivation - loss)
        hp_loss = rng.randint(5, 15)
        state.hp = max(1, state.hp - hp_loss)
        msgs.append(f"[red]突破失败！修为跌落 {loss}，气血 -{hp_loss}。[/]")

    clamp_state(state)
    return state, msgs, roll < success_rate


def _breakthrough_realm(state: PlayerState, rng: random.Random) -> tuple[PlayerState, list[str], bool]:
    """大境界突破（含天劫）"""
    msgs = []
    new_realm = REALMS[state.realm_idx + 1]

    msgs.append(f"[yellow]═══ 冲击 {new_realm.name} ═══[/]")
    msgs.append("[cyan]天地异变，雷云汇聚！天劫降临！[/]")

    trib_config = TRIBULATION_CONFIG
    strikes = trib_config["strikes"]
    success_count = 0

    for i in range(strikes):
        msgs.append(f"\n[yellow]第 {i+1} 道雷劫降临！选择应对方式：[/]")

        chosen = _auto_choose_tribulation(state, rng)
        info = trib_config["options"][chosen]
        cost_attr = info["cost_type"]
        cost_val = info["cost"]
        weight = info["weight"]

        current_val = getattr(state, cost_attr, 0)
        actual_cost = min(cost_val, current_val)
        setattr(state, cost_attr, getattr(state, cost_attr, 0) - actual_cost)

        base_success = 0.6
        rate = min(base_success * weight, 0.95)
        success = rng.random() < rate

        msgs.append(f"[dim]你选择「{chosen}」，消耗 {actual_cost} {_cost_label(cost_attr)}。[/]")
        if success:
            msgs.append(f"[green]⚡ 第 {i+1} 道雷劫成功渡过！[/]")
            success_count += 1
        else:
            dmg = rng.randint(5, 15)
            state.hp = max(1, state.hp - dmg)
            msgs.append(f"[red]⚡ 未能完全抵挡雷劫，气血 -{dmg}！[/]")

    threshold = strikes // 2 + 1
    if success_count >= threshold:
        state.realm_idx += 1
        state.layer = 1
        state.cultivation = 0
        state.max_lifespan += new_realm.base_lifespan_bonus

        state.hp = min(state.max_hp, state.hp + int(state.max_hp * 0.3))
        state.qi = min(state.max_qi, state.qi + int(state.max_qi * 0.3))

        msgs.append(f"[yellow]✦✦✦ 恭喜！你成功踏入 {new_realm.name}！✦✦✦[/]")
        state.add_chronicle(f"大突破！踏入 {new_realm.name}")
    else:
        state.hp = max(1, state.hp - 20)
        state.cultivation = max(0, state.cultivation - int(state.cultivation * 0.3))
        msgs.append("[red]天劫未能完全渡过，突破失败！身受重伤，修为倒退。[/]")
        state.add_chronicle(f"冲击 {new_realm.name} 失败")

    clamp_state(state)
    return state, msgs, success_count >= threshold


def _auto_choose_tribulation(state: PlayerState, rng: random.Random) -> str:
    """自动选择天劫应对方式"""
    options = list(TRIBULATION_CONFIG["options"].items())
    for name, info in options:
        cost_attr = info["cost_type"]
        cost_val = info["cost"]
        if cost_attr == "hp" and state.hp >= cost_val * 2:
            return name
        if cost_attr == "qi" and state.qi >= cost_val * 2:
            return name
        if cost_attr == "spirit_stones" and state.spirit_stones >= cost_val * 2:
            return name
    return "运功硬抗"


def _cost_label(attr: str) -> str:
    labels = {"hp": "气血", "qi": "灵气", "spirit_stones": "灵石"}
    return labels.get(attr, attr)
