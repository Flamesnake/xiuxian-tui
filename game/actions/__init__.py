"""
游戏操作包。

所有 action_* 函数遵循 `(state, rng) → (new_state, messages[])` 的纯函数模式。
"""

from __future__ import annotations

from game.actions.auto import AutoStrategy, auto_tick
from game.actions.breakthrough import action_breakthrough
from game.actions.commerce import action_buy_pill, action_market, action_refine_pill
from game.actions.cultivate import action_batch_cultivate, action_cultivate, action_rest
from game.actions.explore import action_explore
from game.actions.secret_realm import action_enter_secret_realm

__all__ = [
    "action_cultivate",
    "action_batch_cultivate",
    "action_rest",
    "action_explore",
    "action_enter_secret_realm",
    "action_breakthrough",
    "action_market",
    "action_refine_pill",
    "action_buy_pill",
    "auto_tick",
    "AutoStrategy",
]
