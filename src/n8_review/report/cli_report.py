"""CLI 報表（rich）：彩色逐手檢討。"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text

from ..models import TIER_COLOR, Hand, HandEval, QualityTier

console = Console()


def print_parse_summary(hands: list[Hand]) -> None:
    """M1 可用：印解析概況，驗證 parser。"""
    table = Table(title="解析概況")
    table.add_column("項目")
    table.add_column("值", justify="right")
    table.add_row("總手數", str(len(hands)))
    if hands:
        table.add_row("賽事", hands[0].tournament.name)
        table.add_row("Hero 底牌缺漏", str(sum(1 for h in hands if len(h.hero_hole) != 2)))
        table.add_row("含未解析行的手", str(sum(1 for h in hands if h.raw_unparsed)))
    console.print(table)


def print_hand_review(hand: Hand, ev: HandEval) -> None:
    """逐手彩色檢討：整手色塊 + 逐決策上色。TODO(M4) 串接真實 HandEval。"""
    hole = " ".join(str(c) for c in hand.hero_hole)
    head = Text(f"#{hand.hand_id}  [{hole}]  ", style="bold")
    head.append("●", style=TIER_COLOR[ev.hand_tier])
    console.print(head)
    for d in ev.decisions:
        line = Text("  ")
        line.append("●", style=d.color)
        line.append(
            f" {d.street.value:<7} {d.hero_action.type.value:<6} "
            f"EV損失 {d.ev_loss_bb:+.2f}bb  → {d.suggestion.best_action}  {d.explanation}"
        )
        console.print(line)


def print_legend() -> None:
    console.print(
        Text("圖例：")
        .append("● 好 ", style=TIER_COLOR[QualityTier.GOOD])
        .append("● 不準 ", style=TIER_COLOR[QualityTier.INACCURACY])
        .append("● 失誤 ", style=TIER_COLOR[QualityTier.MISTAKE])
        .append("● 未知", style=TIER_COLOR[QualityTier.UNKNOWN])
    )


def print_stats(report: object) -> None:
    """印 StatsReport（GTO 準確率 / EV 損失 / 傳統指標）。"""
    table = Table(title="統計報表")
    table.add_column("指標")
    table.add_column("值", justify="right")
    table.add_row("總手數", str(report.hands))
    table.add_row("GTO 準確率", _pct(report.gto_accuracy))
    table.add_row("EV 損失 / 100手", f"{report.ev_loss_per_100:.2f}bb")
    table.add_row("Mistake 決策", str(report.mistakes))
    table.add_row("VPIP", _pct(report.vpip))
    table.add_row("PFR", _pct(report.pfr))
    table.add_row("3Bet", _pct(report.three_bet))
    table.add_row("C-bet", _pct(report.cbet))
    table.add_row("WTSD", _pct(report.wtsd))
    table.add_row("W$SD", _pct(report.wsd))
    table.add_row("AF", f"{report.aggression_factor:.2f}")
    table.add_row("Net chips", str(report.net_chips))
    console.print(table)

    if report.by_position_net:
        pos = Table(title="位置淨籌碼")
        pos.add_column("位置")
        pos.add_column("Net", justify="right")
        for position, net in sorted(report.by_position_net.items()):
            pos.add_row(position, str(net))
        console.print(pos)


def print_leaks(leaks: list[object]) -> None:
    """依累計 EV 損失列出漏洞 Top-N。"""
    if not leaks:
        console.print("沒有累積的黃/紅漏洞。")
        return
    table = Table(title="漏洞 Top-N")
    table.add_column("模式")
    table.add_column("次數", justify="right")
    table.add_column("累計 EV 損失", justify="right")
    table.add_column("例手")
    for leak in leaks[:10]:
        table.add_row(
            leak.pattern,
            str(leak.count),
            f"{leak.total_ev_loss_bb:.2f}bb",
            ", ".join(leak.example_hand_ids),
        )
    console.print(table)


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"
