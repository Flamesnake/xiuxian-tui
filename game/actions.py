"""
玩家操作系统。
每个操作是纯函数：输入 state → 输出 (new_state, messages[])
不依赖 Textual，方便测试和复用。
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from game.config import (
    ACTION_TIME, PILLS, REALMS, cultivation_needed,
    TRIBULATION_CONFIG, pick_event, pick_chain_event,
    TIMED_EVENTS_CONFIG,
)
from game.state import Buff, PlayerState

if TYPE_CHECKING:
    from ui.app import CultivationApp

# ─── 工具函数 ──────────────────────────────────────────

def _advance_time(state: PlayerState, years: float, rng: random.Random) -> list[str]:
    """推进时间，更新 buff，处理限时事件过期"""
    msgs = []
    state.age += years

    # buff 过期检查
    expired = state.tick_buffs()
    for name in expired:
        msgs.append(f"[dim]状态 [{name}] 已消失。[/]")

    # 限时事件过期
    expired_events = []
    for key, remaining in list(state.timed_events.items()):
        state.timed_events[key] = remaining - 1
        if state.timed_events[key] <= 0:
            expired_events.append(key)
            del state.timed_events[key]
    if "secret_realm" in expired_events:
        msgs.append("[yellow]秘境通道已关闭，错失了一次机缘。[/]")
    # 寿元/气血检查由外部调用判定

    return msgs


def _clamp_state(state: PlayerState) -> None:
    """确保属性在合理范围内"""
    state.hp = max(0, min(state.hp, state.max_hp))
    state.qi = max(0, min(state.qi, state.max_qi))
    state.spirit_stones = max(0, state.spirit_stones)
    state.cultivation = max(0, state.cultivation)


# ─── 基础行动 ──────────────────────────────────────────

def action_cultivate(state: PlayerState, rng: random.Random) -> tuple[PlayerState, list[str]]:
    """修炼：消耗灵气 + 时间 → 获得修为"""
    msgs = []

    # 基础修为获得
    base_gain = 8 + rng.randint(1, 5)

    # 灵气加成（灵气过半有加成，过低有惩罚）
    qi_ratio = state.qi / state.max_qi if state.max_qi > 0 else 0.5
    if qi_ratio > 0.7:
        base_gain = int(base_gain * 1.3)
        msgs.append("[cyan]灵气充沛，修炼效率提升！[/]")
    elif qi_ratio < 0.2:
        base_gain = int(base_gain * 0.6)
        msgs.append("[red]灵气枯竭，修炼事倍功半。[/]")

    # buff 加成
    for b in state.buffs:
        bonus = b.effect.get("cultivation_bonus", 0)
        if bonus:
            base_gain = int(base_gain * (1 + bonus))

    # 气血过低惩罚
    hp_ratio = state.hp / state.max_hp if state.max_hp > 0 else 1
    if hp_ratio < 0.3:
        base_gain = int(base_gain * 0.5)
        msgs.append("[red]身受重伤，难以集中修炼。[/]")

    state.cultivation += base_gain
    state.qi = max(0, state.qi - 3)  # 消耗灵气
    msgs.append(f"[green]修为 +{base_gain}[/]")

    # 小概率触发额外感悟
    if rng.random() < 0.08:
        extra = rng.randint(3, 8)
        state.cultivation += extra
        msgs.append(f"[yellow]心有所悟，额外获得 {extra} 修为！[/]")

    # 推进时间
    time_msgs = _advance_time(state, ACTION_TIME["cultivate"], rng)
    msgs.extend(time_msgs)
    _clamp_state(state)

    return state, msgs


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
        _clamp_state(state)
        time_msgs = _advance_time(state, ACTION_TIME["explore"], rng)
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

    time_msgs = _advance_time(state, ACTION_TIME["explore"], rng)
    msgs.extend(time_msgs)
    _clamp_state(state)

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

    time_msgs = _advance_time(state, ACTION_TIME["rest"], rng)
    msgs.extend(time_msgs)
    _clamp_state(state)

    return state, msgs


def action_refine_pill(state: PlayerState, rng: random.Random) -> tuple[PlayerState, list[str]]:
    """炼丹：消耗灵石 → 获得丹药"""
    msgs = []

    # 简单版：直接消耗灵石炼制指定丹药（简化 MVP）
    # 此处自动炼制聚气丹
    cost = PILLS["聚气丹"]["cost"]
    if state.spirit_stones < cost:
        msgs.append("[red]灵石不足，无法购买炼丹材料。[/]")
        return state, msgs

    state.spirit_stones -= cost

    # 炼丹成功率
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

    time_msgs = _advance_time(state, ACTION_TIME["refine_pill"], rng)
    msgs.extend(time_msgs)
    _clamp_state(state)

    return state, msgs


def action_market(state: PlayerState, rng: random.Random) -> tuple[PlayerState, list[str]]:
    """坊市：买卖物品"""
    msgs = []

    # 简版坊市：卖出 随机获得灵石（基于境界）
    base_income = (state.realm_idx + 1) * 5 + rng.randint(1, 8)

    # 概率遇到打折丹药
    if rng.random() < 0.4:
        discount = rng.randint(1, 3)
        actual_income = base_income + discount
        msgs.append(f"[green]你在坊市卖出一些杂物和草药，获得 {actual_income} 灵石。[/]")
        msgs.append("[yellow]偶遇打折丹药，顺手买了些补充。[/]")
        state.qi = min(state.max_qi, state.qi + rng.randint(3, 6))
    else:
        msgs.append(f"[green]你在坊市卖出收集的材料，获得 {base_income} 灵石。[/]")

    state.spirit_stones += base_income

    time_msgs = _advance_time(state, ACTION_TIME["market"], rng)
    msgs.extend(time_msgs)
    _clamp_state(state)

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
        msgs.append(f"[yellow]护脉丹已生效，下次突破失败反噬减轻。[/]")

    _clamp_state(state)
    return state, msgs


# ─── 突破系统 ──────────────────────────────────────────

def action_breakthrough(state: PlayerState, rng: random.Random, app: CultivationApp | None = None) -> tuple[PlayerState, list[str], bool]:
    """
    尝试突破。
    返回 (state, messages, success)
    """
    msgs = []
    realm = REALMS[state.realm_idx]

    # 检查是否满修为
    needed = state.cultivation_max
    if state.cultivation < needed:
        msgs.append(f"[red]修为不足！({state.cultivation}/{needed})[/]")
        return state, msgs, False

    # 检查是否已达最大境界
    if state.realm_idx >= len(REALMS) - 1 and state.layer >= realm.max_layer:
        msgs.append("[yellow]你已达修仙界巅峰！举霞飞升指日可待。[/]")
        return state, msgs, False

    # 判断是升层还是升大境界
    if state.layer >= realm.max_layer:
        # 大境界突破
        return _breakthrough_realm(state, rng, app)
    else:
        # 小层突破
        return _breakthrough_layer(state, rng)


def _breakthrough_layer(state: PlayerState, rng: random.Random) -> tuple[PlayerState, list[str], bool]:
    """小层突破"""
    msgs = []
    realm = REALMS[state.realm_idx]
    success_rate = realm.breakthrough_base

    # 气血过低降低成功率
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
        # 失败反噬
        loss = int(needed := cultivation_needed(state.realm_idx, state.layer + 1)) // 3
        if state.breakthrough_protected:
            loss = loss // 2
            state.breakthrough_protected = False
            msgs.append("[yellow]护脉丹发挥了作用，反噬减轻。[/]")
        state.cultivation = max(0, state.cultivation - loss)
        hp_loss = rng.randint(5, 15)
        state.hp = max(1, state.hp - hp_loss)
        msgs.append(f"[red]突破失败！修为跌落 {loss}，气血 -{hp_loss}。[/]")

    _clamp_state(state)
    return state, msgs, roll < success_rate


def _breakthrough_realm(state: PlayerState, rng: random.Random, app: CultivationApp | None = None) -> tuple[PlayerState, list[str], bool]:
    """大境界突破（含天劫）"""
    msgs = []
    new_realm = REALMS[state.realm_idx + 1]

    msgs.append(f"[yellow]═══ 冲击 {new_realm.name} ═══[/]")
    msgs.append("[cyan]天地异变，雷云汇聚！天劫降临！[/]")

    # 天劫环节
    trib_config = TRIBULATION_CONFIG
    strikes = trib_config["strikes"]
    success_count = 0

    for i in range(strikes):
        msgs.append(f"\n[yellow]第 {i+1} 道雷劫降临！选择应对方式：[/]")

        # 简单自动选择（如果无 app 交互，则用 AI 自动决策）
        if app:
            # 暂存状态用于 UI 交互
            # 如果 app 可用，会在 UI 层处理交互
            pass

        # 默认自动策略：基于当前资源选择最优方案
        chosen = _auto_choose_tribulation(state, rng)
        info = trib_config["options"][chosen]
        cost_attr = info["cost_type"]
        cost_val = info["cost"]
        weight = info["weight"]

        # 检查资源是否足够
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

    # 判定突破结果
    threshold = strikes // 2 + 1
    if success_count >= threshold:
        state.realm_idx += 1
        state.layer = 1
        state.cultivation = 0
        state.max_lifespan += new_realm.base_lifespan_bonus

        # 突破后大幅恢复
        state.hp = min(state.max_hp, state.hp + int(state.max_hp * 0.3))
        state.qi = min(state.max_qi, state.qi + int(state.max_qi * 0.3))

        msgs.append(f"[yellow]✦✦✦ 恭喜！你成功踏入 {new_realm.name}！✦✦✦[/]")
        state.add_chronicle(f"大突破！踏入 {new_realm.name}")
    else:
        # 突破失败，严重反噬
        state.hp = max(1, state.hp - 20)
        state.cultivation = max(0, state.cultivation - int(state.cultivation * 0.3))
        msgs.append(f"[red]天劫未能完全渡过，突破失败！身受重伤，修为倒退。[/]")
        state.add_chronicle(f"冲击 {new_realm.name} 失败")

    _clamp_state(state)
    return state, msgs, success_count >= threshold


def _auto_choose_tribulation(state: PlayerState, rng: random.Random) -> str:
    """自动选择天劫应对方式"""
    options = list(TRIBULATION_CONFIG["options"].items())
    # 简单策略：选择当前资源最充足的方案
    for name, info in options:
        cost_attr = info["cost_type"]
        cost_val = info["cost"]
        if cost_attr == "hp" and state.hp >= cost_val * 2:
            return name
        if cost_attr == "qi" and state.qi >= cost_val * 2:
            return name
        if cost_attr == "spirit_stones" and state.spirit_stones >= cost_val * 2:
            return name
    # 默认选气血（最基础的）
    return "运功硬抗"


def _cost_label(attr: str) -> str:
    labels = {"hp": "气血", "qi": "灵气", "spirit_stones": "灵石"}
    return labels.get(attr, attr)


# ─── 批量修炼 ──────────────────────────────────────────

def action_batch_cultivate(state: PlayerState, rng: random.Random, count: int = 10) -> tuple[PlayerState, list[str]]:
    """批量修炼：连续执行多次修炼，跳过中间日志只显示总结"""
    total_gain = 0
    total_time = 0
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

        # 检查是否触发了关键事件
        for m in msgs:
            if "秘境" in m or "妖兽" in m or "天劫" in m or "心有所悟" in m:
                events_happened.append(m)
            if "秘境通道已关闭" in m:
                interrupted = True

        if interrupted:
            break

    summary = [
        f"[green]━━━ 批量闭关完成 ━━━[/]",
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


# ─── 秘境事件 ──────────────────────────────────────────

def action_enter_secret_realm(state: PlayerState, rng: random.Random) -> tuple[PlayerState, list[str]]:
    """进入秘境（限时事件）"""
    msgs = []
    if "secret_realm" not in state.timed_events:
        msgs.append("[red]附近没有开启的秘境。[/]")
        return state, msgs

    del state.timed_events["secret_realm"]
    te = TIMED_EVENTS_CONFIG["secret_realm"]

    msgs.append(f"[yellow]══ 进入秘境 ══[/]")
    msgs.append(f"[yellow]{te.description}[/]")

    # 秘境收益（比普通探索高）
    for attr, val in te.effects.items():
        current = getattr(state, attr, 0)
        setattr(state, attr, current + val)
        if attr == "cultivation":
            msgs.append(f"[green]修为 +{val}[/]")
        elif attr == "spirit_stones":
            msgs.append(f"[green]灵石 +{val}[/]")
        elif attr == "hp":
            msgs.append(f"[red]气血 {val}[/]")

    # 额外机缘
    if rng.random() < 0.3:
        bonus = rng.randint(10, 25)
        state.cultivation += bonus
        msgs.append(f"[yellow]你在秘境深处发现上古功法残篇！修为额外 +{bonus}！[/]")

    msgs.append("[green]秘境探索结束，你满载而归。[/]")
    _clamp_state(state)
    return state, msgs


# ─── 辅助函数 ──────────────────────────────────────────

def num_to_cn(n: int) -> str:
    cn = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
    if n <= 9:
        return cn[n]
    return str(n)
