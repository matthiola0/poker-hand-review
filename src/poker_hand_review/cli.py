"""CLI 進入點（typer）。見 SDD §6.1。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from . import config
from .analysis.leaks import aggregate_leaks
from .analysis.stats import compute_stats
from .enrich import build_context
from .evaluate import DecisionEvaluator
from .evaluate.postflop import PostflopBackend, SolverBackendError, get_backend
from .parser import parse_hands, read_file
from .report import cli_report
from .report.json_export import export
from .profile.opponent import ProfileSet, build_profiles
from .web_server import serve_web

app = typer.Typer(add_completion=False, help="n8 手牌歷史 GTO 檢討工具")


def _load(paths: list[Path], hero: str) -> list:
    """讀入檔案或資料夾中所有 .txt，解析成 Hand 清單。"""
    files: list[Path] = []
    for p in paths:
        files.extend(sorted(p.glob("*.txt")) if p.is_dir() else [p])
    hands = []
    for f in files:
        hands.extend(parse_hands(read_file(f), hero))
    return hands


@app.command()
def analyze(
    paths: list[Path] = typer.Argument(..., help="手牌歷史檔或資料夾"),
    hero: str = typer.Option(config.DEFAULT.hero, help="Hero 名稱"),
    postflop: str = typer.Option("equity", help="翻後後端 equity|solver"),
    solver_path: Optional[Path] = typer.Option(None, "--solver-path", help="外部 solver adapter 路徑"),
    min_tier: str = typer.Option("good", help="只顯示此等級以上 good|inaccuracy|mistake"),
    color: bool = typer.Option(True, "--color/--no-color"),
    json_out: Optional[Path] = typer.Option(None, "--json", help="同時匯出 JSON"),
) -> None:
    """逐手彩色 GTO 檢討 + 統計 + 漏洞。"""
    hands = _load(paths, hero)
    cli_report.print_parse_summary(hands)
    cli_report.print_legend()
    contexts = [build_context(hand) for hand in hands]
    profiles = build_profiles(hands, hero)
    evaluator = DecisionEvaluator(
        _postflop_backend(postflop, solver_path),
        opponent_range_keys=_range_keys(profiles),
    )
    hand_evals = _evaluate_all(evaluator, hands, contexts)
    min_rank = _tier_rank(min_tier)
    for hand, hand_eval in zip(hands, hand_evals):
        if _tier_rank(hand_eval.hand_tier.value) >= min_rank:
            cli_report.print_hand_review(hand, hand_eval)
    stats = compute_stats(hands, contexts, hand_evals)
    leaks = aggregate_leaks(hand_evals)
    cli_report.print_stats(stats)
    cli_report.print_leaks(leaks)
    if json_out:
        export(
            {
                "hands": hands,
                "hero_contexts": contexts,
                "hand_evals": hand_evals,
                "stats": stats,
                "opponents": profiles.by_player,
                "leaks": leaks,
            },
            str(json_out),
        )
        typer.echo(f"JSON 已輸出：{json_out}")


@app.command()
def hand(
    path: Path = typer.Argument(...),
    id: str = typer.Option(..., "--id", help="手牌 ID，如 TM6030071921"),
    hero: str = typer.Option(config.DEFAULT.hero),
    postflop: str = typer.Option("equity"),
    solver_path: Optional[Path] = typer.Option(None, "--solver-path", help="外部 solver adapter 路徑"),
) -> None:
    """單手逐街深度檢討（含 equity / GTO 建議）。TODO(M3-M4)。"""
    all_hands = _load([path], hero)
    hands = [h for h in all_hands if h.hand_id == id]
    if not hands:
        raise typer.BadParameter(f"找不到手牌 {id}")
    ctx = build_context(hands[0])
    profiles = build_profiles(all_hands, hero)
    evaluator = DecisionEvaluator(
        _postflop_backend(postflop, solver_path),
        opponent_range_keys=_range_keys(profiles),
    )
    cli_report.print_hand_review(hands[0], _evaluate_one(evaluator, hands[0], ctx))


@app.command()
def stats(
    paths: list[Path] = typer.Argument(...),
    hero: str = typer.Option(config.DEFAULT.hero),
) -> None:
    """統計（GTO 準確率 / EV 損失 / 傳統指標）。TODO(M2/M4)。"""
    hands = _load(paths, hero)
    contexts = [build_context(hand) for hand in hands]
    profiles = build_profiles(hands, hero)
    evaluator = DecisionEvaluator(
        get_backend("equity", mc_samples=config.DEFAULT.mc_samples),
        opponent_range_keys=_range_keys(profiles),
    )
    hand_evals = [evaluator.evaluate_hand(hand, ctx) for hand, ctx in zip(hands, contexts)]
    cli_report.print_stats(compute_stats(hands, contexts, hand_evals))


@app.command()
def profile(
    paths: list[Path] = typer.Argument(...),
    hero: str = typer.Option(config.DEFAULT.hero),
) -> None:
    """對手群像。TODO(M5)。"""
    hands = _load(paths, hero)
    profiles = build_profiles(hands, hero)
    for profile in sorted(profiles.by_player.values(), key=lambda p: p.hands, reverse=True):
        typer.echo(
            f"{profile.player}: hands={profile.hands} VPIP={profile.vpip:.1%} "
            f"PFR={profile.pfr:.1%} 3Bet={profile.three_bet:.1%} "
            f"tags={','.join(profile.tags)}"
        )


@app.command()
def web(
    report: Optional[Path] = typer.Option(None, "--report", help="預先載入的 JSON report"),
    solver_path: Optional[Path] = typer.Option(None, "--solver-path", help="外部 solver adapter 路徑"),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8765, "--port"),
    solver_timeout_sec: int = typer.Option(120, "--solver-timeout"),
) -> None:
    """啟動 Web UI 本機 server；有 --solver-path 時可在 UI 內執行 solver。"""
    root = Path(__file__).resolve().parents[2]
    if report is not None and not report.exists():
        raise typer.BadParameter(f"找不到 report: {report}")
    if solver_path is not None and not solver_path.exists():
        raise typer.BadParameter(f"找不到 solver adapter: {solver_path}")
    url = f"http://{host}:{port}/"
    typer.echo(f"Web UI: {url}")
    if solver_path:
        typer.echo("UI solver: enabled")
    else:
        typer.echo("UI solver: disabled（加上 --solver-path 可啟用）")
    serve_web(
        root=root,
        report_path=report,
        solver_path=solver_path or (Path(config.DEFAULT.solver_path) if config.DEFAULT.solver_path else None),
        host=host,
        port=port,
        solver_timeout_sec=solver_timeout_sec,
    )


def _tier_rank(tier: str) -> int:
    ranks = {"good": 0, "unknown": 0, "inaccuracy": 1, "mistake": 2}
    if tier not in ranks:
        raise typer.BadParameter("min-tier 必須是 good|inaccuracy|mistake")
    return ranks[tier]


def _range_keys(profiles: ProfileSet) -> dict[str, str | None]:
    return {
        player: profile.assumed_range_key
        for player, profile in profiles.by_player.items()
    }


def _postflop_backend(postflop: str, solver_path: Optional[Path]) -> PostflopBackend:
    if postflop == "solver":
        configured_path = str(solver_path) if solver_path else config.DEFAULT.solver_path
        return get_backend("solver", solver_path=configured_path)
    if postflop == "equity":
        return get_backend("equity", mc_samples=config.DEFAULT.mc_samples)
    raise typer.BadParameter("postflop 必須是 equity|solver")


def _evaluate_all(
    evaluator: DecisionEvaluator,
    hands: list,
    contexts: list,
) -> list:
    try:
        return [evaluator.evaluate_hand(hand, ctx) for hand, ctx in zip(hands, contexts)]
    except SolverBackendError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _evaluate_one(evaluator: DecisionEvaluator, hand: object, ctx: object) -> object:
    try:
        return evaluator.evaluate_hand(hand, ctx)  # type: ignore[arg-type]
    except SolverBackendError as exc:
        raise typer.BadParameter(str(exc)) from exc


if __name__ == "__main__":
    app()
