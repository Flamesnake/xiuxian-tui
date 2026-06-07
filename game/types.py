"""
修仙模拟器 — 数据类型定义。

集中存放所有核心数据类（NamedTuple / dataclass），
供 config（配置数据）、state（玩家状态）和 actions（操作逻辑）共同引用。
避免循环导入，保持单一数据定义源。
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import NamedTuple


class Realm(NamedTuple):
    """一个大境界的定义"""
    name: str          # e.g. "炼气期"
    icon: str          # e.g. "🟢"
    max_layer: int     # 该境界包含多少小层
    base_lifespan_bonus: int   # 突破到该境界时增加寿元
    layer_lifespan_bonus: int  # 每突破一小层增加寿元
    breakthrough_base: float   # 小突破基础概率 (0~1)
    tribulation: bool          # 是否触发天劫（大境界突破）


class EventTemplate(NamedTuple):
    """随机事件模板"""
    title: str
    description: str
    color: str          # Rich markup color
    effects: dict       # 属性变更
    tags: list[str]     # 标签


class TimedEvent(NamedTuple):
    """限时事件定义"""
    key: str
    name: str
    duration: int        # 剩余行动次数
    description: str
    effects: dict


@dataclass
class Buff:
    """状态效果（buff / debuff）"""
    name: str
    remaining: int       # 剩余行动次数
    effect: dict         # {"hp_regen": 2, "cultivation_bonus": 0.1}

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Buff:
        return cls(**data)


@dataclass
class ChronicleEntry:
    """修仙年表中的一条记录"""
    year: float          # 游戏内年龄（发生时）
    text: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ChronicleEntry:
        return cls(**data)
