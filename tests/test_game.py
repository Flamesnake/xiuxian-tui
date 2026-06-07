"""
游戏逻辑核心的单元测试。

测试策略：
- game/ 是纯逻辑层，不依赖 UI，完全可测。
- 每个 action_* 函数都是 (state, rng) → (new_state, messages) 的纯函数。
- 测试关注状态变更的正确性，而非随机输出（使用固定 seed）。
"""
from __future__ import annotations

import random

from game.actions import (
    action_batch_cultivate,
    action_breakthrough,
    action_cultivate,
    action_explore,
    action_market,
    action_refine_pill,
    action_rest,
)
from game.state import Buff, PlayerState


def test_state_roundtrip() -> None:
    """PlayerState 序列化/反序列化不变性"""
    state = PlayerState(name="测试散修", seed=42, realm_idx=1, layer=3)
    state.cultivation = 500
    state.add_chronicle("踏上修仙之路")
    state.buffs.append(Buff(name="灵气护体", remaining=5, effect={"cultivation_bonus": 0.1}))

    data = state.to_dict()
    restored = PlayerState.from_dict(data)

    assert restored.name == state.name
    assert restored.realm_idx == state.realm_idx
    assert restored.layer == state.layer
    assert restored.cultivation == state.cultivation
    assert len(restored.chronicle) == 1
    assert restored.chronicle[0].text == "踏上修仙之路"
    assert len(restored.buffs) == 1
    assert restored.buffs[0].name == "灵气护体"


def test_cultivate_increases_cultivation() -> None:
    """修炼增加修为"""
    state = PlayerState(seed=42)
    rng = random.Random(42)
    old_cult = state.cultivation

    new_state, msgs = action_cultivate(state, rng)

    assert new_state.cultivation > old_cult
    assert any("修为" in m for m in msgs)


def test_cultivate_consumes_qi() -> None:
    """修炼消耗灵气"""
    state = PlayerState(seed=42, qi=50)
    rng = random.Random(42)

    new_state, _ = action_cultivate(state, rng)

    assert new_state.qi < 50


def test_rest_restores_hp() -> None:
    """休息恢复气血"""
    state = PlayerState(seed=42, hp=30, max_hp=100)
    rng = random.Random(42)

    new_state, msgs = action_rest(state, rng)

    assert new_state.hp > 30
    assert any("气血" in m for m in msgs)


def test_rest_restores_qi() -> None:
    """休息恢复灵气"""
    state = PlayerState(seed=42, qi=10, max_qi=50)
    rng = random.Random(42)

    new_state, _ = action_rest(state, rng)

    assert new_state.qi > 10


def test_refine_pill_insufficient_funds() -> None:
    """灵石不足时炼丹失败"""
    state = PlayerState(seed=42, spirit_stones=0)
    rng = random.Random(42)

    new_state, msgs = action_refine_pill(state, rng)

    assert "灵石不足" in msgs[0]
    assert new_state.spirit_stones == 0


def test_market_earns_spirit_stones() -> None:
    """坊市交易获得灵石"""
    state = PlayerState(seed=42, spirit_stones=0)
    rng = random.Random(42)

    new_state, msgs = action_market(state, rng)

    assert new_state.spirit_stones > 0
    assert any("灵石" in m for m in msgs)


def test_breakthrough_requires_full_cultivation() -> None:
    """修为不足时突破失败"""
    state = PlayerState(seed=42, cultivation=0)
    rng = random.Random(42)

    _, msgs, ok = action_breakthrough(state, rng)

    assert not ok
    assert any("不足" in m for m in msgs)


def test_breakthrough_success() -> None:
    """修为满时突破成功"""
    state = PlayerState(seed=42, realm_idx=0, layer=1,
                        cultivation=10_000, hp=100)
    rng = random.Random(42)

    new_state, _, ok = action_breakthrough(state, rng)

    assert ok
    assert new_state.layer > 1 or new_state.realm_idx > 0
    assert new_state.cultivation < 10_000  # 突破后修为重置/减少


def test_is_dead_by_hp() -> None:
    """气血归零则死亡"""
    state = PlayerState(hp=0)
    assert state.is_dead


def test_is_dead_by_age() -> None:
    """寿元耗尽则死亡"""
    state = PlayerState(age=100, max_lifespan=100)
    assert state.is_dead


def test_batch_cultivate() -> None:
    """批量修炼累积修为"""
    state = PlayerState(seed=42, cultivation=0)
    rng = random.Random(42)

    new_state, msgs = action_batch_cultivate(state, rng, count=5)

    assert new_state.cultivation > 0
    assert any("总增长" in m for m in msgs)


def test_buff_expiry() -> None:
    """buff 每回合减少剩余时间，过期后移除"""
    state = PlayerState(seed=42)
    state.buffs.append(Buff(name="测试", remaining=2, effect={}))

    # tick twice → buff should expire
    state.tick_buffs()
    assert len(state.buffs) == 1

    state.tick_buffs()
    assert len(state.buffs) == 0


def test_explore_advances_age() -> None:
    """探索消耗时间，年龄增长"""
    state = PlayerState(seed=42, age=16.0)
    rng = random.Random(42)

    new_state, _ = action_explore(state, rng)

    assert new_state.age > 16.0


def test_num_to_cn_small() -> None:
    """数字转中文"""
    from game.state import num_to_cn
    assert num_to_cn(1) == "一"
    assert num_to_cn(5) == "五"
    assert num_to_cn(10) == "十"
    assert num_to_cn(15) == "十五"
    assert num_to_cn(23) == "二十三"


# ─── 自动挂机测试 ─────────────────────────────────────────

def test_auto_decision_cultivate() -> None:
    """修为未满时自动返回 cultivate"""
    state = PlayerState(seed=42, cultivation=0, hp=100, max_hp=100, qi=50, max_qi=50)
    from game.actions.auto import AutoStrategy
    decision = AutoStrategy().decide(state)
    assert decision == "cultivate"


def test_auto_decision_rest_low_hp() -> None:
    """HP 过低时自动返回 rest"""
    state = PlayerState(seed=42, cultivation=0, hp=10, max_hp=100, qi=50, max_qi=50)
    from game.actions.auto import AutoStrategy
    decision = AutoStrategy().decide(state)
    assert decision == "rest"


def test_auto_decision_rest_low_qi() -> None:
    """灵气过低时自动返回 rest"""
    state = PlayerState(seed=42, cultivation=0, hp=100, max_hp=100, qi=5, max_qi=50)
    from game.actions.auto import AutoStrategy
    decision = AutoStrategy().decide(state)
    assert decision == "rest"


def test_auto_decision_full_cultivation() -> None:
    """修为满时返回 None（等待玩家）"""
    state = PlayerState(seed=42, realm_idx=0, layer=1, cultivation=10_000, hp=100, max_hp=100, qi=50, max_qi=50)
    from game.actions.auto import AutoStrategy
    decision = AutoStrategy().decide(state)
    assert decision is None


def test_auto_decision_dead() -> None:
    """死亡时返回 None"""
    state = PlayerState(seed=42, hp=0)
    from game.actions.auto import AutoStrategy
    decision = AutoStrategy().decide(state)
    assert decision is None


def test_auto_tick_cultivate() -> None:
    """auto_tick 执行修炼并返回 action_name"""
    state = PlayerState(seed=42, cultivation=0, hp=100, max_hp=100, qi=50, max_qi=50)
    rng = random.Random(42)
    from game.actions.auto import auto_tick

    new_state, msgs, action = auto_tick(state, rng)
    assert action == "cultivate"
    assert new_state.cultivation > 0
    assert len(msgs) > 0


def test_auto_tick_rest() -> None:
    """auto_tick 执行休息并返回 action_name"""
    state = PlayerState(seed=42, hp=10, max_hp=100, qi=50, max_qi=50, cultivation=0)
    rng = random.Random(42)
    from game.actions.auto import auto_tick

    new_state, msgs, action = auto_tick(state, rng)
    assert action == "rest"
    assert new_state.hp > 10


def test_auto_tick_idle() -> None:
    """auto_tick 在满修为时返回 action='idle'"""
    state = PlayerState(seed=42, realm_idx=0, layer=1, cultivation=10_000, hp=100, max_hp=100, qi=50, max_qi=50)
    rng = random.Random(42)
    from game.actions.auto import auto_tick

    new_state, msgs, action = auto_tick(state, rng)
    assert action == "idle"
    assert len(msgs) == 0


def test_auto_strategy_custom_config() -> None:
    """自定义策略阈值生效"""
    from game.actions.auto import AutoStrategy
    # 默认 HP 阈值 0.3，设置为 0.8 后应更早休息
    state = PlayerState(seed=42, hp=70, max_hp=100, qi=50, max_qi=50, cultivation=0)
    strategy = AutoStrategy().with_config(hp_threshold=0.8)
    decision = strategy.decide(state)
    assert decision == "rest"  # HP=70 < 80%
