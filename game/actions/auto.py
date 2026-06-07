"""
自动挂机引擎。

决策树控制修炼和休息的自动循环，玩家只需观察数值增长。
突破、探索、炼丹等策略性操作仍由玩家手动触发。
"""

from __future__ import annotations

import random

from game.actions.cultivate import action_cultivate, action_rest
from game.state import PlayerState


class AutoStrategy:
    """自动挂机策略——纯逻辑，无 UI 依赖。

    决策树优先级：
      1. 死亡 → None（停止）
      2. HP < 阈值 → rest
      3. Qi < 阈值 → rest
      4. 修为未满 → cultivate
      5. 修为满 → None（等待玩家突破/探索）

    配置项可通过 with_config() 调整，未来可在 UI 中由玩家设置。
    """

    hp_threshold: float = 0.3
    qi_threshold: float = 0.2

    def with_config(self, **kwargs) -> AutoStrategy:
        """链式配置（预留 UI 接口）"""
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    def decide(self, state: PlayerState) -> str | None:
        """根据玩家状态决定下一步自动动作。

        Returns:
            "cultivate" | "rest" | None（等待玩家操作）
        """
        if state.is_dead:
            return None

        if state.hp < state.max_hp * self.hp_threshold:
            return "rest"

        if state.qi < state.max_qi * self.qi_threshold:
            return "rest"

        if state.cultivation < state.cultivation_max:
            return "cultivate"

        return None


ACTION_NAMES: dict[str, str] = {
    "cultivate": "修炼",
    "rest": "休息",
}


def auto_tick(state: PlayerState, rng: random.Random, strategy: AutoStrategy | None = None) -> tuple[PlayerState, list[str], str | None]:
    """执行一步自动挂机。

    Args:
        state: 当前玩家状态（会被修改）
        rng: 随机数生成器
        strategy: 策略对象，None 则使用默认策略

    Returns:
        (new_state, messages, action_name)
        action_name: "idle" 等待操作 | "dead" 已死亡 | None 不应发生
    """
    if strategy is None:
        strategy = AutoStrategy()

    if state.is_dead:
        return state, [], "dead"

    decision = strategy.decide(state)
    if decision is None:
        return state, [], "idle"

    action_fn = {
        "rest": action_rest,
        "cultivate": action_cultivate,
    }[decision]

    new_state, msgs = action_fn(state, rng)
    return new_state, msgs, decision
