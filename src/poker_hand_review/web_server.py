"""Local Web UI server with an optional solver endpoint."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from . import config
from .analysis.leaks import aggregate_leaks
from .analysis.stats import compute_stats
from .evaluate.evaluator import DecisionEvaluator, _explain, _postflop_ev_loss
from .evaluate.postflop import (
    PostflopBackend,
    PostflopNode,
    SolverBackend,
    SolverBackendError,
    get_backend,
)
from .evaluate.quality import QualityThresholds, tier_from_ev_loss
from .models import Action, ActionType, Card, DecisionEval, Street, parse_card
from .parser import parse_hands, split_hands
from .profile.opponent import build_profiles
from .report.json_export import SCHEMA_VERSION, _jsonable
from .enrich import Decision, build_context

# Cap request bodies so a single POST can't exhaust memory.
_MAX_BODY_BYTES = 16 * 1024 * 1024  # 16 MiB
# Loopback names always allowed for Host / Origin checks (the bound host is
# added on top in WebServerConfig so a custom --host still works).
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", ""})


class WebServerConfig:
    def __init__(
        self,
        root: Path,
        report_path: Path | None,
        solver_path: Path | None,
        solver_timeout_sec: int,
        host: str = "127.0.0.1",
    ) -> None:
        self.root = root
        self.web_root = root / "web"
        self.report_path = report_path
        self.solver_path = solver_path
        self.solver_timeout_sec = solver_timeout_sec
        self.host = host
        self.allowed_hosts = frozenset(_LOOPBACK_HOSTS | {host})


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
    config = WebServerConfig(root, report_path, solver_path, solver_timeout_sec, host)

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
        if parsed.path == "/api/data-files":
            try:
                self._send_json(list_data_files_payload(self.server_config))
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
            return
        self._send_static(parsed.path)

    def do_POST(self) -> None:  # noqa: N802 - stdlib hook
        if not self._guard_local_request():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/analyze":
            try:
                payload = self._read_json()
                result = analyze_payload(payload, self.server_config)
            except (ValueError, SolverBackendError) as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            self._send_json(result)
            return
        if parsed.path == "/api/analyze-data":
            try:
                payload = self._read_json()
                result = analyze_data_payload(payload, self.server_config)
            except (ValueError, SolverBackendError) as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            self._send_json(result)
            return
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

    def _guard_local_request(self) -> bool:
        """Block cross-site / non-loopback POSTs (CSRF + DNS-rebinding defense).

        The API can run a local solver binary, so a malicious web page must not
        be able to drive it. We require a loopback Host, reject any cross-origin
        Origin, and require a JSON content type (which also forces a CORS
        preflight a hostile page can't satisfy).
        """
        allowed = self.server_config.allowed_hosts
        host = (self.headers.get("host") or "").rsplit(":", 1)[0].strip("[]").lower()
        if host not in allowed:
            self._send_json({"error": "forbidden host"}, status=403)
            return False
        origin = self.headers.get("origin")
        if origin is not None and origin != "null":
            origin_host = (urlparse(origin).hostname or "").lower()
            if origin_host not in allowed:
                self._send_json({"error": "cross-origin request forbidden"}, status=403)
                return False
        ctype = (self.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
        if ctype != "application/json":
            self._send_json({"error": "content-type must be application/json"}, status=415)
            return False
        return True

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError as exc:
            raise ValueError("invalid content-length") from exc
        if length < 0 or length > _MAX_BODY_BYTES:
            raise ValueError("request body too large")
        raw = self.rfile.read(length)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("request body must be a JSON object")
        return data

    def _send_static(self, raw_path: str) -> None:
        rel = unquote(raw_path.lstrip("/"))
        target = (self.server_config.root / rel).resolve()
        web_root = self.server_config.web_root.resolve()
        try:
            target.relative_to(web_root)
        except ValueError:
            self._send_json({"error": "not found"}, status=404)
            return
        if not target.exists() or target.is_dir():
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


def analyze_payload(payload: dict[str, Any], config_obj: WebServerConfig) -> dict[str, Any]:
    """逐檔分析上傳的 .txt 手牌歷史。

    每個來源檔各自快取在 ``data/analyzed/`` 下；內容沒變就直接讀快取，
    回傳 ``{"reports": [...]}`` 由前端 ``mergeReports`` 合併。
    """
    hero = str(payload.get("hero") or config.DEFAULT.hero)
    postflop = str(payload.get("postflop") or "equity")
    refresh = bool(payload.get("refresh"))
    sources = _collect_sources(payload)

    backend: PostflopBackend | None = None
    reports: list[dict[str, Any]] = []
    for filename, text in sources:
        cache_path = _cache_path(config_obj, filename)
        source_hash = _source_hash(hero, text)
        if not refresh:
            cached = _read_valid_cache(cache_path, source_hash)
            if cached is not None:
                reports.append(cached)
                continue
        if backend is None:
            backend = _analyze_backend(postflop, config_obj)
        report = _analyze_one(filename, text, hero, backend)
        if report is None:
            continue
        _write_cache(cache_path, report, source_hash)
        report["from_cache"] = False
        reports.append(report)

    if not reports:
        raise ValueError("找不到手牌（檔案需含 'Poker Hand #' 區塊）")
    return {"reports": reports}


def _analyze_one(
    filename: str, text: str, hero: str, backend: PostflopBackend
) -> dict[str, Any] | None:
    """把單一檔案的手牌跑完整 pipeline，回傳與 report.json 相同結構。"""
    hands = parse_hands(split_hands(text), hero)
    if not hands:
        return None
    contexts = [build_context(hand) for hand in hands]
    profiles = build_profiles(hands, hero)
    evaluator = DecisionEvaluator(
        backend,
        opponent_range_keys={
            player: profile.assumed_range_key
            for player, profile in profiles.by_player.items()
        },
    )
    try:
        hand_evals = [evaluator.evaluate_hand(hand, ctx) for hand, ctx in zip(hands, contexts)]
    except SolverBackendError as exc:
        raise ValueError(str(exc)) from exc
    report = {
        "schema": SCHEMA_VERSION,
        "hands": hands,
        "hero_contexts": contexts,
        "hand_evals": hand_evals,
        "stats": compute_stats(hands, contexts, hand_evals),
        "opponents": profiles.by_player,
        "leaks": aggregate_leaks(hand_evals),
    }
    result: dict[str, Any] = _jsonable(report)
    for hand in result["hands"]:
        hand["source_file"] = filename
    return result


def _collect_sources(payload: dict[str, Any]) -> list[tuple[str, str]]:
    """把 payload 整理成 (filename, text) 清單；跳過空白內容。"""
    sources = payload.get("sources")
    if sources is not None:
        if not isinstance(sources, list):
            raise ValueError("sources 必須是檔案陣列")
        collected: list[tuple[str, str]] = []
        for source in sources:
            if not isinstance(source, dict):
                raise ValueError("sources 必須是檔案陣列")
            filename = str(source.get("filename") or "Uploaded text")
            text = source.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            collected.append((filename, text))
        return collected

    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("missing hand-history text")
    filename = str(payload.get("filename") or "Uploaded text")
    return [(filename, text)]


CACHE_DIRNAME = "analyzed"


def _cache_dir(config_obj: WebServerConfig) -> Path:
    return config_obj.root / "data" / CACHE_DIRNAME


def _cache_path(config_obj: WebServerConfig, filename: str) -> Path:
    """把來源檔名對應到固定的快取檔路徑（同名來源 → 同一快取檔）。"""
    stem = Path(str(filename)).name
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", stem) or "source"
    return _cache_dir(config_obj) / f"{safe}.json"


def _source_hash(hero: str, text: str) -> str:
    digest = hashlib.sha256()
    digest.update(hero.encode("utf-8"))
    digest.update(b"\0")
    digest.update(text.encode("utf-8"))
    return digest.hexdigest()


def _read_valid_cache(cache_path: Path, source_hash: str) -> dict[str, Any] | None:
    """快取存在且內容雜湊相符時回傳報告，否則回傳 None。"""
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    meta = data.get("_cache")
    if not isinstance(meta, dict) or meta.get("source_hash") != source_hash:
        return None
    data.pop("_cache", None)
    data["from_cache"] = True
    return data


def _write_cache(cache_path: Path, report: dict[str, Any], source_hash: str) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**report, "_cache": {"source_hash": source_hash, "schema": SCHEMA_VERSION}}
    _write_report(cache_path, payload)


def analyze_data_payload(payload: dict[str, Any], config_obj: WebServerConfig) -> dict[str, Any]:
    """讀取專案 data 資料夾中的 .txt 手牌歷史，回傳 Web report。"""
    files = _data_files(config_obj, payload.get("files"))
    if not files:
        raise ValueError("data 資料夾沒有 .txt 手牌檔")
    request = dict(payload)
    request["sources"] = [
        {
            "filename": path.name,
            "text": path.read_text(encoding="utf-8-sig"),
        }
        for path in files
    ]
    return analyze_payload(request, config_obj)


def list_data_files_payload(config_obj: WebServerConfig) -> dict[str, Any]:
    """列出專案 data 資料夾中的 .txt 檔，供 Web UI 勾選。"""
    files = _data_files(config_obj, None)
    if not files:
        raise ValueError("data 資料夾沒有 .txt 手牌檔")
    return {
        "files": [
            {
                "name": path.name,
                "size": path.stat().st_size,
                "hand_count": len(split_hands(path.read_text(encoding="utf-8-sig"))),
            }
            for path in files
        ]
    }


def _data_files(config_obj: WebServerConfig, selected: Any) -> list[Path]:
    data_dir = config_obj.root / "data"
    available = {path.name: path for path in sorted(data_dir.glob("*.txt"))} if data_dir.is_dir() else {}
    if selected is None:
        return list(available.values())
    if not isinstance(selected, list) or not all(isinstance(item, str) for item in selected):
        raise ValueError("files 必須是檔名陣列")
    files: list[Path] = []
    for name in selected:
        path = available.get(name)
        if path is None:
            raise ValueError(f"invalid data file: {name}")
        files.append(path)
    return files


def _analyze_backend(postflop: str, config_obj: WebServerConfig) -> PostflopBackend:
    if postflop == "equity":
        return get_backend("equity", mc_samples=config.DEFAULT.mc_samples)
    if postflop == "solver":
        # The solver path is fixed at server startup (--solver-path); it is never
        # taken from the request body, so a web page can't point it at an
        # arbitrary executable.
        if config_obj.solver_path is None:
            raise ValueError(
                "solver 後端需在啟動時以 --solver-path 設定（不接受請求指定路徑）"
            )
        path = str(config_obj.solver_path)
        if not Path(path).exists():
            raise ValueError(f"找不到 solver adapter: {path}")
        return get_backend("solver", solver_path=path)
    raise ValueError("postflop 必須是 equity|solver")


def solve_payload(payload: dict[str, Any], config: WebServerConfig) -> dict[str, Any]:
    if config.solver_path is None:
        raise SolverBackendError("UI solver requires starting poker-hand-review web with --solver-path")

    hand_id = str(payload.get("hand_id", ""))
    decision_index = _decision_index(payload.get("decision_index"))
    target_path = _solve_target_path(payload, config)
    previous = _previous_decision_eval(target_path, hand_id, decision_index)
    node = _postflop_node(payload.get("node"))
    decision = _decision(payload.get("decision"), node)
    backend = SolverBackend(
        solver_path=str(config.solver_path),
        timeout_sec=config.solver_timeout_sec,
    )
    suggestion = backend.evaluate(node)
    ev_loss = _postflop_ev_loss(decision, suggestion, node.bb)
    tier = tier_from_ev_loss(ev_loss, QualityThresholds())
    text, key, params = _explain(decision, suggestion, ev_loss)
    evaluation = DecisionEval(
        hand_id=str(payload.get("hand_id", "")),
        street=node.street,
        hero_action=decision.hero_action,
        suggestion=suggestion,
        ev_loss_bb=ev_loss,
        tier=tier,
        explanation=text,
        explanation_key=key,
        explanation_params=params,
    )
    decision_eval = _jsonable(asdict(evaluation))
    decision_eval["solver_delta"] = _solver_delta(previous, decision_eval)
    result: dict[str, Any] = {"decision_eval": decision_eval, "saved": False}
    if target_path is not None:
        result.update(_persist_solver_result(target_path, hand_id, decision_index, decision_eval))
    return result


def _solve_target_path(payload: dict[str, Any], config: WebServerConfig) -> Path | None:
    """solver 結果要覆寫的報告檔：優先寫回該手牌來源檔的快取，否則 --report 檔。"""
    source_file = payload.get("source_file")
    if isinstance(source_file, str) and source_file.strip():
        candidate = _cache_path(config, source_file)
        if candidate.exists():
            return candidate
    if config.report_path is not None and config.report_path.exists():
        return config.report_path
    return None


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
    stats: dict[str, Any] = report.setdefault("stats", {})
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
    return str(max(tiers, key=lambda tier: severity.get(tier, severity["unknown"])))


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


def _cards(raw: Any, expected: int | None = None) -> tuple[Card, ...]:
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
