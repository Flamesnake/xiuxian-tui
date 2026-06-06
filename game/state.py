"""
玩家状态数据模型。
使用 dataclass 管理全部属性，支持序列化/反序列化。
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any

from game.config import REALMS, PLAYER_INIT

@dataclass
class Buff:
    """状态效果"""
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


@dataclass
class PlayerState:
    """玩家全部状态"""
    name: str = PLAYER_INIT["name"]
    realm_idx: int = PLAYER_INIT["realm_idx"]    # 境界索引
    layer: int = PLAYER_INIT["layer"]            # 当前小层 (1-based)
    hp: int = PLAYER_INIT["hp"]
    max_hp: int = PLAYER_INIT["max_hp"]
    qi: int = PLAYER_INIT["qi"]
    max_qi: int = PLAYER_INIT["max_qi"]
    cultivation: int = PLAYER_INIT["cultivation"]           # 当前修为
    max_lifespan: int = PLAYER_INIT["max_lifespan"]         # 寿元上限
    age: float = float(PLAYER_INIT["age"])                  # 当前年龄
    spirit_stones: int = PLAYER_INIT["spirit_stones"]
    buffs: list[Buff] = field(default_factory=list)
    chronicle: list[ChronicleEntry] = field(default_factory=list)

    # 事件链追踪（用于因果链）
    pending_chain_event: str | None = None   # 触发因果链的 key
    timed_events: dict[str, int] = field(default_factory=dict)  # {event_key: remaining_actions}

    # 突破保护（服用护脉丹后）
    breakthrough_protected: bool = False

    # 种子（用于后续随机生成系统）
    seed: int = 0

    @property
    def realm_name(self) -> str:
        if 0 <= self.realm_idx < len(REALMS):
            return REALMS[self.realm_idx].name
        return "未知"

    @property
    def realm_icon(self) -> str:
        if 0 <= self.realm_idx < len(REALMS):
            return REALMS[self.realm_idx].icon
        return "❓"

    @property
    def layer_display(self) -> str:
        return f"{num_to_cn(self.layer)}层"

    @property
    def title_display(self) -> str:
        """完整境界显示，如 🟢 炼气期三层"""
        return f"{self.realm_icon} {self.realm_name}{self.layer_display}"

    @property
    def lifespan_remaining(self) -> float:
        return round(self.max_lifespan - self.age, 2)

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0 or self.age >= self.max_lifespan

    @property
    def cultivation_max(self) -> int:
        """当前层突破所需修为"""
        from game.config import cultivation_needed
        return cultivation_needed(self.realm_idx, self.layer + 1)

    @property
    def cultivation_progress(self) -> float:
        """修为进度 0~1"""
        total = self.cultivation_max
        if total == 0:
            return 1.0
        return min(self.cultivation / total, 1.0)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "realm_idx": self.realm_idx,
            "layer": self.layer,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "qi": self.qi,
            "max_qi": self.max_qi,
            "cultivation": self.cultivation,
            "max_lifespan": self.max_lifespan,
            "age": self.age,
            "spirit_stones": self.spirit_stones,
            "buffs": [b.to_dict() for b in self.buffs],
            "chronicle": [c.to_dict() for c in self.chronicle],
            "pending_chain_event": self.pending_chain_event,
            "timed_events": dict(self.timed_events),
            "breakthrough_protected": self.breakthrough_protected,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PlayerState:
        buffs = [Buff.from_dict(b) for b in data.pop("buffs", [])]
        chronicle = [ChronicleEntry.from_dict(c) for c in data.pop("chronicle", [])]
        state = cls(**data)
        state.buffs = buffs
        state.chronicle = chronicle
        return state

    def add_chronicle(self, text: str) -> None:
        """添加一条修仙年表记录"""
        self.chronicle.append(ChronicleEntry(year=round(self.age, 1), text=text))

    def has_buff(self, name: str) -> bool:
        return any(b.name == name for b in self.buffs)

    def tick_buffs(self) -> list[str]:
        """每回合更新 buff 剩余时间，返回过期的 buff 名称列表"""
        expired = []
        for b in self.buffs[:]:
            b.remaining -= 1
            if b.remaining <= 0:
                self.buffs.remove(b)
                expired.append(b.name)
        return expired


def num_to_cn(n: int) -> str:
    """数字转中文数字"""
    cn = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
          "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九"]
    if n < len(cn):
        return cn[n]
    tens = n // 10
    ones = n % 10
    if ones == 0:
        return cn[tens] + "十"
    return cn[tens] + "十" + cn[ones]
