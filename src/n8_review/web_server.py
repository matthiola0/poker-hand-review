"""Local Web UI server with an optional solver endpoint."""

from __future__ import annotations

from dataclasses import asdict
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .evaluate.evaluator import _explain, _postflop_ev_loss
from .evaluate.postflop import PostflopNode, SolverBackend, SolverBackendError
from .evaluate.quality import QualityThresholds, tier_from_ev_loss
from .models import Action, ActionType, DecisionEval, GtoSuggestion, Street, parse_card
from .report.json_export import _jsonable
from .enrich import Decision


class WebServerConfig:
    def __init__(
        self,
        root: Path,
        report_path: Path | None,
        solver_path: Path | None,
        solver_timeout_sec: int,
    ) -> None:
        self.root = root
        self.web_root = root / "web"
        self.report_path = report_path
        self.solver_path = solver_path
        self.solver_timeout_sec = solver_timeout_sec


def serve_web(
    *,
    root: Path,
    report_path: Path | None,
    solver_path: Path | None,
    host: str,
    port: int,
    solver_timeout_sec: int = 120,
) -> None:
    """Start the local Web UI server and block forever."""
    config = WebServerConfig(root, report_path, solver_path, solver_timeout_sec)

    class Handler(N8ReviewHandler):
        server_config = config

    server = ThreadingHTTPServer((host, port), Handler)
    server.serve_forever()


class N8ReviewHandler(BaseHTTPRequestHandler):
    server_config: WebServerConfig

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook
        parsed = urlparse(self.path)
        if parsed.path == "/":
            suffix = "?report=/report.json" if self.server_config.report_path else ""
            self._redirect(f"/web/index.html{suffix}")
            return
        if parsed.path == "/report.json" and self.server_config.report_path:
            self._send_file(self.server_config.report_path)
            return
        self._send_static(parsed.path)

    def do_POST(self) -> None:  # noqa: N802 - stdlib hook
        parsed = urlparse(self.path)
        if parsed.path != "/api/solve":
            self._send_json({"error": "not found"}, status=404)
            return

        try:
            payload = self._read_json()
            result = solve_payload(payload, self.server_config)
        except (ValueError, SolverBackendError) as exc:
            self._send_json({"error": str(exc)}, status=400)
            return
        self._send_json(result)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("request body must be a JSON object")
        return data

    def _send_static(self, raw_path: str) -> None:
        rel = unquote(raw_path.lstrip("/"))
        target = (self.server_config.root / rel).resolve()
        web_root = self.server_config.web_root.resolve()
        if not str(target).startswith(str(web_root)) or not target.exists() or target.is_dir():
            self._send_json({"error": "not found"}, status=404)
            return
        self._send_file(target)

    def _send_file(self, path: Path) -> None:
        suffix = path.suffix.lower()
        mime = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png",
        }.get(suffix, "application/octet-stream")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("content-type", mime)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, location: str) -> None:
        self.send_response(302)
        self.send_header("location", location)
        self.end_headers()


def solve_payload(payload: dict[str, Any], config: WebServerConfig) -> dict[str, Any]:
    if config.solver_path is None:
        raise SolverBackendError("UI solver requires starting n8-review web with --solver-path")

    hand_id = str(payload.get("hand_id", ""))
    decision_index = _decision_index(payload.get("decision_index"))
    previous = _previous_decision_eval(config.report_path, hand_id, decision_index)
    node = _postflop_node(payload.get("node"))
    decision = _decision(payload.get("decision"), node)
    backend = SolverBackend(
        solver_path=str(config.solver_path),
        timeout_sec=config.solver_timeout_sec,
    )
    suggestion = backend.evaluate(node)
    ev_loss = _postflop_ev_loss(decision, suggestion, node.bb)
    tier = tier_from_ev_loss(ev_loss, QualityThresholds())
    evaluation = DecisionEval(
        hand_id=str(payload.get("hand_id", "")),
        street=node.street,
        hero_action=decision.hero_action,
        suggestion=suggestion,
        ev_loss_bb=ev_loss,
        tier=tier,
        explanation=_explain(decision, suggestion, ev_loss),
    )
    decision_eval = _jsonable(asdict(evaluation))
    decision_eval["solver_delta"] = _solver_delta(previous, decision_eval)
    result: dict[str, Any] = {"decision_eval": decision_eval, "saved": False}
    if config.report_path is not None:
        result.update(_persist_solver_result(config.report_path, hand_id, decision_index, decision_eval))
    return result


def _decision_index(raw: Any) -> int:
    try:
        index = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("missing decision_index") from exc
    if index < 0:
        raise ValueError("decision_index must be >= 0")
    return index


def _previous_decision_eval(report_path: Path | None, hand_id: str, decision_index: int) -> dict[str, Any] | None:
    if report_path is None or not report_path.exists():
        return None
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    hand_eval = _find_hand_eval(report, hand_id)
    decisions = hand_eval.get("decisions", []) if hand_eval else []
    if decision_index >= len(decisions):
        return None
    previous = decisions[decision_index]
    return previous if isinstance(previous, dict) else None


def _persist_solver_result(
    report_path: Path,
    hand_id: str,
    decision_index: int,
    decision_eval: dict[str, Any],
) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    hand_eval = _find_hand_eval(report, hand_id)
    if hand_eval is None:
        raise ValueError(f"report missing hand_eval for {hand_id}")
    decisions = hand_eval.get("decisions")
    if not isinstance(decisions, list) or decision_index >= len(decisions):
        raise ValueError(f"report missing decision index {decision_index} for {hand_id}")

    decisions[decision_index] = decision_eval
    hand_eval["hand_tier"] = _worst_tier(decisions)
    stats = _refresh_solver_stats(report)
    _write_report(report_path, report)
    return {
        "saved": True,
        "stats": stats,
        "hand_tier": hand_eval["hand_tier"],
    }


def _find_hand_eval(report: dict[str, Any], hand_id: str) -> dict[str, Any] | None:
    for hand_eval in report.get("hand_evals", []):
        if isinstance(hand_eval, dict) and hand_eval.get("hand_id") == hand_id:
            return hand_eval
    return None


def _refresh_solver_stats(report: dict[str, Any]) -> dict[str, Any]:
    stats = report.setdefault("stats", {})
    decisions = [
        decision
        for hand_eval in report.get("hand_evals", [])
        if isinstance(hand_eval, dict)
        for decision in hand_eval.get("decisions", [])
        if isinstance(decision, dict) and decision.get("tier") != "unknown"
    ]
    total_hands = int(stats.get("hands") or len(report.get("hands", [])) or 0)
    good = sum(1 for decision in decisions if decision.get("tier") == "good")
    mistakes = sum(1 for decision in decisions if decision.get("tier") == "mistake")
    total_ev_loss = sum(float(decision.get("ev_loss_bb") or 0) for decision in decisions)
    stats["gto_accuracy"] = good / len(decisions) if decisions else 0.0
    stats["ev_loss_per_100"] = (total_ev_loss / total_hands * 100) if total_hands else 0.0
    stats["mistakes"] = mistakes
    return stats


def _write_report(report_path: Path, report: dict[str, Any]) -> None:
    tmp = report_path.with_name(f"{report_path.name}.tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(report_path)


def _worst_tier(decisions: list[Any]) -> str:
    severity = {"good": 0, "unknown": 1, "inaccuracy": 2, "mistake": 3}
    tiers = [decision.get("tier", "unknown") for decision in decisions if isinstance(decision, dict)]
    if not tiers:
        return "unknown"
    return max(tiers, key=lambda tier: severity.get(tier, severity["unknown"]))


def _solver_delta(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if previous is None:
        return {
            "status": "new",
            "direction": "flat",
            "changed": True,
            "summary": "new solver result",
        }

    prev_best = _best_action(previous)
    next_best = _best_action(current)
    prev_tier = str(previous.get("tier", "unknown"))
    next_tier = str(current.get("tier", "unknown"))
    prev_ev = float(previous.get("ev_loss_bb") or 0)
    next_ev = float(current.get("ev_loss_bb") or 0)
    ev_delta = prev_ev - next_ev
    tier_delta = _tier_severity(prev_tier) - _tier_severity(next_tier)
    changed = prev_best != next_best or prev_tier != next_tier or abs(ev_delta) >= 0.01
    direction = "flat"
    if tier_delta > 0 or ev_delta >= 0.01:
        direction = "up"
    elif tier_delta < 0 or ev_delta <= -0.01:
        direction = "down"
    summary = "no change"
    if prev_best != next_best:
        summary = f"best {prev_best or 'n/a'} -> {next_best or 'n/a'}"
    elif prev_tier != next_tier:
        summary = f"tier {prev_tier} -> {next_tier}"
    elif abs(ev_delta) >= 0.01:
        summary = f"EV {ev_delta:+.2f}bb"
    return {
        "status": "changed" if changed else "unchanged",
        "direction": direction,
        "changed": changed,
        "previous_best_action": prev_best,
        "best_action": next_best,
        "previous_tier": prev_tier,
        "tier": next_tier,
        "ev_loss_delta_bb": ev_delta,
        "summary": summary,
    }


def _best_action(decision_eval: dict[str, Any]) -> str:
    suggestion = decision_eval.get("suggestion")
    if not isinstance(suggestion, dict):
        return ""
    return str(suggestion.get("best_action", ""))


def _tier_severity(tier: str) -> int:
    return {"good": 0, "unknown": 1, "inaccuracy": 2, "mistake": 3}.get(tier, 1)


def _postflop_node(raw: Any) -> PostflopNode:
    if not isinstance(raw, dict):
        raise ValueError("missing node")
    return PostflopNode(
        street=Street(raw["street"]),
        hero_hole=_cards(raw["hero_hole"], expected=2),  # type: ignore[arg-type]
        board=_cards(raw.get("board", ())),
        pot_before=int(raw["pot_before"]),
        to_call=int(raw["to_call"]),
        eff_stack=int(raw["eff_stack"]),
        villain_range_key=raw.get("villain_range_key"),
        bb=int(raw["bb"]),
    )


def _decision(raw: Any, node: PostflopNode) -> Decision:
    if not isinstance(raw, dict):
        raise ValueError("missing decision")
    hero_action = _action(raw.get("hero_action"))
    return Decision(
        street=node.street,
        facing=str(raw.get("facing", "checked")),
        villain=raw.get("villain"),
        pot_before=node.pot_before,
        to_call=node.to_call,
        hero_action=hero_action,
        pot_odds=raw.get("pot_odds"),
    )


def _action(raw: Any) -> Action:
    if not isinstance(raw, dict):
        raise ValueError("missing hero_action")
    return Action(
        player=str(raw.get("player", "Hero")),
        type=ActionType(raw["type"]),
        amount=int(raw.get("amount", 0)),
        to_amount=int(raw.get("to_amount", 0)),
        all_in=bool(raw.get("all_in", False)),
    )


def _cards(raw: Any, expected: int | None = None) -> tuple:
    if not isinstance(raw, list):
        raise ValueError("cards must be a list")
    cards = tuple(parse_card(_card_text(card)) for card in raw)
    if expected is not None and len(cards) != expected:
        raise ValueError(f"expected {expected} cards")
    return cards


def _card_text(card: Any) -> str:
    if isinstance(card, str):
        return card
    if isinstance(card, dict):
        return f"{card.get('rank')}{card.get('suit')}"
    raise ValueError("invalid card")
