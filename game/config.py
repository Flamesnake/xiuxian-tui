"""
境界体系、事件表、丹药效果、数值公式。
所有游戏常量集中在此，方便调整平衡性。
"""

from __future__ import annotations
import random
from typing import NamedTuple

# ─── 境界体系 ───────────────────────────────────────────

class Realm(NamedTuple):
    """一个大境界的定义"""
    name: str          # e.g. "炼气期"
    icon: str          # e.g. "🟢"
    max_layer: int     # 该境界包含多少小层
    base_lifespan_bonus: int   # 突破到该境界时增加寿元
    layer_lifespan_bonus: int  # 每突破一小层增加寿元
    breakthrough_base: float   # 小突破基础概率 (0~1)
    tribulation: bool          # 是否触发天劫（大境界突破）

REALMS: list[Realm] = [
    Realm("炼气期", "🟢", 9, 0, 1, 0.80, False),
    Realm("筑基期", "🔵", 6, 30, 2, 0.65, True),
    Realm("金丹期", "🟣", 4, 50, 3, 0.50, True),
]

# 大境界突破天劫配置
TRIBULATION_CONFIG = {
    "strikes": 3,           # 几道雷劫
    "options": {            # 应对选项: (消耗资源, 消耗量, 成功率权重)
        "运功硬抗": {"cost_type": "hp", "cost": 15, "weight": 1.0},
        "身法躲避": {"cost_type": "qi", "cost": 20, "weight": 1.2},
        "法器抵挡": {"cost_type": "spirit_stones", "cost": 30, "weight": 1.4},
    },
}

# ─── 修为需求公式 ──────────────────────────────────────

# 修为 = base_per_layer * (layer ^ exponent)
REALM_CULTIVATION_BASE: dict[int, float] = {
    0: 100,   # 炼气期 基础每层 100
    1: 500,   # 筑基期 基础每层 500
    2: 2000,  # 金丹期 基础每层 2000
}
CULTIVATION_EXPONENT = 1.5

def cultivation_needed(realm_idx: int, layer: int) -> int:
    """计算突破到下一层需要的修为值"""
    base = REALM_CULTIVATION_BASE[realm_idx]
    return int(base * (layer ** CULTIVATION_EXPONENT)) or base

# ─── 初始属性 ──────────────────────────────────────────

PLAYER_INIT = {
    "name": "无名散修",
    "realm_idx": 0,       # 初始炼气期
    "layer": 1,           # 炼气一层
    "hp": 100,
    "max_hp": 100,
    "qi": 50,
    "max_qi": 50,
    "cultivation": 0,     # 当前修为
    "max_lifespan": 60,   # 寿元上限（年）
    "age": 16,            # 当前年龄
    "spirit_stones": 10,  # 灵石
    "buffs": [],          # 状态效果列表
}

# ─── 行动时间消耗（年） ──────────────────────────────────

ACTION_TIME = {
    "cultivate": 0.10,   # 修炼 ~36.5天
    "meditate": 0.05,    # 冥想 ~18天
    "explore": 0.05,     # 探索
    "rest": 0.01,        # 休息 ~3.65天
    "refine_pill": 0.08, # 炼丹 ~29天
    "market": 0.03,      # 坊市 ~11天
    "batch_cultivate": 0.10,  # 每次批量修炼
}

# ─── 丹药效果 ──────────────────────────────────────────

PILLS = {
    "聚气丹": {
        "cost": 5,
        "effects": {"cultivation": 15, "qi": 10},
        "desc": "基础修炼丹药，增加修为并补充灵气",
    },
    "回春丹": {
        "cost": 3,
        "effects": {"hp": 30},
        "desc": "基础疗伤丹药，恢复气血",
    },
    "蕴神丹": {
        "cost": 8,
        "effects": {"qi": 25, "cultivation": 5},
        "desc": "补充神识，恢复大量灵气",
    },
    "护脉丹": {
        "cost": 15,
        "effects": {"breakthrough_protect": True},
        "desc": "突破时服用，减轻失败反噬",
    },
}

# ─── 随机事件配置 ──────────────────────────────────────

class EventTemplate(NamedTuple):
    title: str
    description: str
    color: str          # Rich markup color
    effects: dict       # 属性变更
    tags: list[str]     # 标签

# 炼气期事件池
EVENTS_REALM_0 = [
    EventTemplate(
        "发现灵草", "你在山涧中发现一株百年灵芝，小心翼翼采集后售予坊市。",
        "green", {"spirit_stones": 8}, ["herb", "positive"],
    ),
    EventTemplate(
        "妖兽袭击", "一只赤眼野狼突袭你的洞府，你奋力将其击退，但受了些轻伤。",
        "red", {"hp": -10}, ["beast", "combat", "negative"],
    ),
    EventTemplate(
        "前辈遗迹", "在古树下发现一位散修遗留的玉简，记录了一些修炼心得，有所感悟。",
        "yellow", {"cultivation": 20}, ["legacy", "positive"],
    ),
    EventTemplate(
        "灵气潮汐", "今日天地灵气异常充沛，修炼效率大增！",
        "cyan", {"cultivation": 25}, ["qi_tide", "positive", "special"],
    ),
    EventTemplate(
        "切磋邀请", "一位路过散修邀你切磋论道，虽败犹荣，学到不少。",
        "cyan", {"cultivation": 8}, ["social", "neutral"],
    ),
    EventTemplate(
        "灵泉沐浴", "你发现一眼隐藏的灵泉，浸泡后气血和灵气都得到恢复。",
        "green", {"hp": 15, "qi": 15}, ["herb", "positive"],
    ),
    EventTemplate(
        "走火入魔", "修炼时心绪不宁，灵气逆行，受了内伤。",
        "red", {"hp": -20, "cultivation": -10}, ["negative", "danger"],
    ),
    EventTemplate(
        "采药遭劫", "采药时被毒蜂蜇伤，虽采集到几株草药，但需休养。",
        "red", {"hp": -8, "spirit_stones": 3}, ["negative", "herb"],
    ),
    EventTemplate(
        "月下悟道", "月圆之夜，独坐山巅，感悟天地之道，修为精进。",
        "yellow", {"cultivation": 30}, ["positive", "special"],
    ),
]

# 筑基期事件池
EVENTS_REALM_1 = [
    EventTemplate(
        "秘境入口", "你发现一处小型秘境入口！里面灵气浓郁，但似乎有妖兽守护。",
        "yellow", {"cultivation": 40, "spirit_stones": 15}, ["secret_realm", "positive"],
    ),
    EventTemplate(
        "拍卖大会", "坊市举办拍卖会，你淘到一件不错的法器材料。",
        "green", {"spirit_stones": -5}, ["market", "neutral"],
    ),
    EventTemplate(
        "妖兽巢穴", "你发现一群妖兽的巢穴，击败后获得不少修炼资源。",
        "yellow", {"hp": -15, "spirit_stones": 20, "cultivation": 15}, ["combat", "positive"],
    ),
    EventTemplate(
        "魔修偷袭", "一名魔修暗中偷袭，你奋力反击，双方各有损伤。",
        "red", {"hp": -25, "spirit_stones": 10}, ["combat", "negative"],
    ),
    EventTemplate(
        "古修洞府", "找到一位金丹期散修的坐化洞府，获得遗留的修炼心得。",
        "yellow", {"cultivation": 50}, ["legacy", "positive", "special"],
    ),
    EventTemplate(
        "地火爆发", "修炼之地突发地火，你仓促逃离，损失了些物品。",
        "red", {"hp": -15, "spirit_stones": -8}, ["negative", "disaster"],
    ),
    EventTemplate(
        "论道大会", "参加散修论道会，与诸位道友交流心得，获益良多。",
        "cyan", {"cultivation": 20}, ["social", "positive"],
    ),
]

# 金丹期事件池
EVENTS_REALM_2 = [
    EventTemplate(
        "天降陨铁", "一块天外陨铁坠落在附近，蕴含稀有材料，引来多人争夺。",
        "yellow", {"spirit_stones": 30, "hp": -10}, ["combat", "positive"],
    ),
    EventTemplate(
        "秘境深处", "深入古秘境，发现一株千年灵药！但守护兽实力强劲。",
        "yellow", {"hp": -20, "cultivation": 60}, ["secret_realm", "positive", "special"],
    ),
    EventTemplate(
        "魔门暗流", "卷入魔门与正道之争，被迫出手，身负重伤。",
        "red", {"hp": -35, "cultivation": 15}, ["combat", "negative"],
    ),
    EventTemplate(
        "天劫预兆", "你感应到天劫将至的征兆，天地异变，需做好准备。",
        "cyan", {}, ["omen", "neutral", "special"],
    ),
    EventTemplate(
        "道友来访", "一位金丹期道友来访，与你交流炼丹心得，赠送了些丹药。",
        "green", {"hp": 20, "qi": 20}, ["social", "positive"],
    ),
]

# 按境界索引的事件池
EVENT_POOLS = [EVENTS_REALM_0, EVENTS_REALM_1, EVENTS_REALM_2]

# ─── 事件因果链 ──────────────────────────────────────

EVENT_CHAINS: dict[str, list[EventTemplate]] = {
    "herb_found": [
        EventTemplate("移植灵草", "你将灵草移植到洞府附近，灵气滋养下长势喜人，每次修炼获得额外加成。", "green", {"qi": 10}, ["buff", "positive"]),
        EventTemplate("出售灵草", "你将灵草在坊市卖出好价钱。", "green", {"spirit_stones": 15}, ["market", "positive"]),
    ],
    "beast_attack": [
        EventTemplate("追踪巢穴", "你追踪妖兽来到其巢穴，发现不少修炼资源！", "yellow", {"spirit_stones": 15, "cultivation": 10, "hp": -10}, ["combat", "positive"]),
    ],
}

# 限时事件：持续 N 次行动后消失
class TimedEvent(NamedTuple):
    key: str
    name: str
    duration: int        # 剩余行动次数
    description: str
    effects: dict

TIMED_EVENTS_CONFIG = {
    "secret_realm": TimedEvent(
        key="secret_realm",
        name="秘境开启",
        duration=3,
        description="附近的秘境通道已经开启，灵气四溢。进入探索可能获得大机缘！",
        effects={"cultivation": 50, "spirit_stones": 20, "hp": -10},
    ),
}

# ─── 事件选择逻辑 ─────────────────────────────────────

def pick_event(realm_idx: int, rng: random.Random) -> EventTemplate | None:
    """从当前境界事件池随机选取一个事件。30%概率不触发。"""
    if rng.random() < 0.30:
        return None
    pool = EVENT_POOLS[realm_idx]
    return rng.choice(pool)

def pick_chain_event(chain_key: str, rng: random.Random) -> EventTemplate | None:
    """从因果链中选取后续事件"""
    chain = EVENT_CHAINS.get(chain_key)
    if not chain:
        return None
    return rng.choice(chain)
