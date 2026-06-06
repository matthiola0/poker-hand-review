"""選用翻後後端：透過外部 solver adapter 對關鍵手深解。

SolverBackend 不假設 TexasSolver 原生 CLI 格式；它定義一個小型 JSON
adapter contract，讓 TexasSolver 包裝器或測試替身都能穩定接入：

    solver_path <input.json>

外部程序從 stdout 回傳策略 JSON，例如：

    {"actions": {"call": 0.72, "fold": 0.28}, "best_action": "call"}

這讓核心引擎保持可測試，也避免在尚未確認本機 solver binary 前把格式寫死。
"""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from ...models import GtoSuggestion
from .base import PostflopNode


class SolverBackendError(RuntimeError):
    """外部 solver 無法執行或回傳格式不合法。"""


class SolverBackend:
    name = "solver"

    def __init__(
        self,
        solver_path: str | None = None,
        timeout_sec: int = 120,
        solver_args: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self.solver_path = solver_path or os.getenv("PHR_SOLVER_PATH") or os.getenv(
            "TEXAS_SOLVER_PATH"
        )
        self.timeout_sec = timeout_sec
        self.solver_args = tuple(solver_args or ())

    def evaluate(self, node: PostflopNode) -> GtoSuggestion:
        """以 Hero/對手範圍 + board 呼叫外部 solver adapter，回傳策略。"""
        if not self.solver_path:
            raise SolverBackendError(
                "solver 後端需要 --solver-path，或設定 PHR_SOLVER_PATH/TEXAS_SOLVER_PATH"
            )

        solver = Path(self.solver_path)
        if not solver.exists():
            raise SolverBackendError(f"找不到 solver adapter: {solver}")

        payload = _node_payload(node)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            input_path = f.name

        try:
            result = subprocess.run(
                [str(solver), *self.solver_args, input_path],
                capture_output=True,
                check=False,
                encoding="utf-8",
                timeout=self.timeout_sec,
            )
        except subprocess.TimeoutExpired as exc:
            raise SolverBackendError(f"solver 超時（>{self.timeout_sec}s）") from exc
        finally:
            Path(input_path).unlink(missing_ok=True)

        if result.returncode != 0:
            stderr = result.stderr.strip() or "no stderr"
            raise SolverBackendError(f"solver 執行失敗 exit={result.returncode}: {stderr}")
        if not result.stdout.strip():
            raise SolverBackendError("solver 沒有輸出策略 JSON 到 stdout")

        try:
            strategy = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise SolverBackendError("solver stdout 不是合法 JSON") from exc

        actions, best_action = _parse_strategy(strategy)
        return GtoSuggestion(actions=actions, best_action=best_action, source="solver")


def _node_payload(node: PostflopNode) -> dict[str, Any]:
    data = asdict(node)
    data["street"] = node.street.value
    data["hero_hole"] = [str(card) for card in node.hero_hole]
    data["board"] = [str(card) for card in node.board]
    data["candidate_actions"] = (
        ["fold", "call", "raise"] if node.to_call > 0 else ["check", "bet"]
    )
    data["contract"] = "poker_hand_review.solver_node.v1"
    return data


def _parse_strategy(strategy: Any) -> tuple[tuple[tuple[str, float], ...], str]:
    if not isinstance(strategy, dict):
        raise SolverBackendError("solver strategy 必須是 JSON object")

    raw_actions = strategy.get("actions") or strategy.get("strategy")
    actions = _parse_actions(raw_actions)
    if not actions:
        raise SolverBackendError("solver strategy 缺少 actions/strategy")

    best_action = strategy.get("best_action")
    if not isinstance(best_action, str) or not best_action:
        best_action = max(actions, key=lambda item: item[1])[0]
    return tuple(actions), best_action


def _parse_actions(raw_actions: Any) -> list[tuple[str, float]]:
    if isinstance(raw_actions, dict):
        return [_action_pair(action, freq) for action, freq in raw_actions.items()]

    if isinstance(raw_actions, list):
        parsed: list[tuple[str, float]] = []
        for item in raw_actions:
            if isinstance(item, dict):
                action = item.get("action")
                freq = item.get("frequency", item.get("freq"))
                parsed.append(_action_pair(action, freq))
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                parsed.append(_action_pair(item[0], item[1]))
            else:
                raise SolverBackendError("solver action entry 格式不合法")
        return parsed

    raise SolverBackendError("solver actions 格式不合法")


def _action_pair(action: Any, freq: Any) -> tuple[str, float]:
    if not isinstance(action, str) or not action:
        raise SolverBackendError("solver action 名稱不合法")
    try:
        value = float(freq)
    except (TypeError, ValueError) as exc:
        raise SolverBackendError("solver action frequency 不合法") from exc
    if value < 0:
        raise SolverBackendError("solver action frequency 不可為負")
    return action, value
