"""
随机事件引擎。
事件由 actions 模块调用，此处提供事件检查和特殊状态管理。
MVP 中事件逻辑已整合在 config.py（事件池）和 actions.py（触发）中，
本模块提供辅助函数供外部检查事件状态。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.config import TIMED_EVENTS_CONFIG

if TYPE_CHECKING:
    from game.state import PlayerState


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
