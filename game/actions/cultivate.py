"""
修炼、休息、批量闭关。
"""

from __future__ import annotations

import random

from game.actions._shared import advance_time, clamp_state
from game.config import ACTION_TIME
from game.state import PlayerState


def action_cultivate(state: PlayerState, rng: random.Random) -> tuple[PlayerState, list[str]]:
    """修炼：消耗灵气 + 时间 → 获得修为"""
    msgs = []

    base_gain = 8 + rng.randint(1, 5)

    qi_ratio = state.qi / state.max_qi if state.max_qi > 0 else 0.5
    if qi_ratio > 0.7:
        base_gain = int(base_gain * 1.3)
        msgs.append("[cyan]灵气充沛，修炼效率提升！[/]")
    elif qi_ratio < 0.2:
        base_gain = int(base_gain * 0.6)
        msgs.append("[red]灵气枯竭，修炼事倍功半。[/]")

    for b in state.buffs:
        bonus = b.effect.get("cultivation_bonus", 0)
        if bonus:
            base_gain = int(base_gain * (1 + bonus))

    hp_ratio = state.hp / state.max_hp if state.max_hp > 0 else 1
    if hp_ratio < 0.3:
        base_gain = int(base_gain * 0.5)
        msgs.append("[red]身受重伤，难以集中修炼。[/]")

    state.cultivation += base_gain
    state.qi = max(0, state.qi - 3)
    msgs.append(f"[green]修为 +{base_gain}[/]")

    if rng.random() < 0.08:
        extra = rng.randint(3, 8)
        state.cultivation += extra
        msgs.append(f"[yellow]心有所悟，额外获得 {extra} 修为！[/]")

    time_msgs = advance_time(state, ACTION_TIME["cultivate"], rng)
    msgs.extend(time_msgs)
    clamp_state(state)

    return state, msgs


def action_rest(state: PlayerState, rng: random.Random) -> tuple[PlayerState, list[str]]:
    """休息：消耗少量时间 → 恢复气血和灵气"""
    msgs = []

    hp_recovery = int(state.max_hp * 0.3) + rng.randint(1, 5)
    qi_recovery = int(state.max_qi * 0.2) + rng.randint(1, 3)

    old_hp, old_qi = state.hp, state.qi
    state.hp = min(state.max_hp, state.hp + hp_recovery)
    state.qi = min(state.max_qi, state.qi + qi_recovery)

    actual_hp = state.hp - old_hp
    actual_qi = state.qi - old_qi
    if actual_hp > 0:
        msgs.append(f"[green]气血 +{actual_hp}[/]")
    if actual_qi > 0:
        msgs.append(f"[cyan]灵气 +{actual_qi}[/]")
    msgs.append("[dim]你闭目养神，身心舒缓。[/]")

    time_msgs = advance_time(state, ACTION_TIME["rest"], rng)
    msgs.extend(time_msgs)
    clamp_state(state)

    return state, msgs


def action_batch_cultivate(state: PlayerState, rng: random.Random, count: int = 10) -> tuple[PlayerState, list[str]]:
    """批量修炼：连续执行多次修炼，跳过中间日志只显示总结"""
    total_gain = 0
    total_time = 0.0
    events_happened = []
    interrupted = False

    for i in range(count):
        if state.is_dead:
            break
        if state.cultivation >= state.cultivation_max:
            msgs = [f"[yellow]修为已满，可尝试突破！({state.cultivation}/{state.cultivation_max})[/]"]
            return state, msgs

        state_prev = state.cultivation
        state, msgs = action_cultivate(state, rng)
        gain = state.cultivation - state_prev

        total_gain += gain
        total_time += ACTION_TIME["batch_cultivate"]

        for m in msgs:
            if "秘境" in m or "妖兽" in m or "天劫" in m or "心有所悟" in m:
                events_happened.append(m)
            if "秘境通道已关闭" in m:
                interrupted = True

        if interrupted:
            break

    summary = [
        "[green]━━━ 批量闭关完成 ━━━[/]",
        f"[green]修为总增长：+{total_gain}[/]",
    ]
    if events_happened:
        summary.append("[yellow]闭关期间事件：[/]")
        for e in events_happened[:5]:
            summary.append(f"  {e}")
    if len(events_happened) > 5:
        summary.append(f"  [dim]...及其他 {len(events_happened)-5} 条[/]")
    if interrupted:
        summary.append("[red]闭关因紧急事件中断。[/]")

    return state, summary
