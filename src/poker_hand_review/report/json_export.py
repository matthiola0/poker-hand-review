"""JSON 匯出：核心引擎與 Web UI 之間的穩定契約。

含 schema 版本號，Web UI 依此版本相容。輸出結構（SDD §5.5）：
  { schema, hands, hero_contexts, stats, findings }
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"


def export(payload: dict, path: str) -> None:
    """把分析結果寫成 JSON。"""
    data = {"schema": SCHEMA_VERSION, **payload}
    Path(path).write_text(
        json.dumps(_jsonable(data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value
