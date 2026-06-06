"""
存档系统：JSON 格式，支持自动存档、滚动备份。
存档文件保存在 data/saves/ 目录下。
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from game.state import PlayerState

SAVE_DIR = Path("data") / "saves"
AUTOSAVE_PATH = SAVE_DIR / "autosave.json"
MAX_BACKUPS = 3


def _ensure_save_dir() -> None:
    """确保存档目录存在"""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)


def _rotate_backups() -> None:
    """滚动备份：将 autosave.json 轮转为 autosave.1.json → .2.json → .3.json"""
    autosave = AUTOSAVE_PATH
    if not autosave.exists():
        return

    # 删除最旧的备份
    oldest = SAVE_DIR / f"autosave.{MAX_BACKUPS}.json"
    if oldest.exists():
        oldest.unlink()

    # 依次后移
    for i in range(MAX_BACKUPS - 1, 0, -1):
        src = SAVE_DIR / f"autosave.{i}.json"
        dst = SAVE_DIR / f"autosave.{i + 1}.json"
        if src.exists():
            shutil.move(str(src), str(dst))

    # 当前存档 → .1
    shutil.move(str(autosave), str(SAVE_DIR / "autosave.1.json"))


def save_game(state: PlayerState, manual: bool = False) -> str:
    """
    保存游戏状态到 JSON 文件。
    Args:
        state: 当前玩家状态
        manual: 是否手动存档（手动存档单独命名为手动存档）
    Returns:
        存档路径字符串
    """
    _ensure_save_dir()

    data = state.to_dict()
    data["save_version"] = "0.1.0"

    if manual:
        # 手动存档：单独的文件，不参与滚动备份
        path = SAVE_DIR / f"manual_{state.name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(path)
    else:
        # 自动存档：先备份再写入
        _rotate_backups()
        with open(AUTOSAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(AUTOSAVE_PATH)


def load_game(path: str | None = None) -> PlayerState | None:
    """
    从 JSON 文件加载游戏状态。
    Args:
        path: 存档路径，None 则尝试加载自动存档
    Returns:
        PlayerState 或 None（无存档）
    """
    if path is None:
        path = str(AUTOSAVE_PATH)

    p = Path(path)
    if not p.exists():
        return None

    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 移除存档元数据
        data.pop("save_version", None)
        return PlayerState.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"[存档错误] 无法读取存档: {e}")
        return None


def has_save() -> bool:
    """检查是否存在自动存档"""
    return AUTOSAVE_PATH.exists()


def list_saves() -> list[dict]:
    """列出所有可用存档"""
    _ensure_save_dir()
    saves = []
    for f in sorted(SAVE_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        saves.append({
            "name": f.name,
            "path": str(f),
            "mtime": os.path.getmtime(f),
        })
    return saves


def delete_save(path: str) -> bool:
    """删除指定存档"""
    try:
        Path(path).unlink()
        return True
    except OSError:
        return False
