"""
utils/distribute_tokens.py
──────────────────────────
Tính toán phân bổ token cho cổ đông trước khi deploy.
Chạy độc lập (không cần blockchain):
    python utils/distribute_tokens.py

Kết quả xuất ra console + file utils/distribution_plan.json
"""

from __future__ import annotations
import json
import math
from dataclasses import dataclass, asdict
from typing import Literal
from pathlib import Path


# ─── Constants ────────────────────────────────────────────────────────────────
TOTAL_HST      = 10_000_000          # Tổng cung (đơn vị HST, chưa nhân 10^18)
DECIMALS       = 10 ** 18
TIER_THRESHOLDS = {
    3: 0.30,   # Sáng lập:   ≥ 30%
    2: 0.10,   # Chiến lược: ≥ 10%
    1: 0.01,   # Tổ chức:    ≥ 1%
    0: 0.00,   # Nhỏ lẻ:     < 1%
}


# ─── Data Classes ─────────────────────────────────────────────────────────────
@dataclass
class Shareholder:
    address:  str
    name:     str
    shares:   int        # Số cổ phiếu thực tế (input)
    hst:      int = 0    # Số HST được phân bổ (output)
    tier:     int = 0
    pct:      float = 0.0


@dataclass
class DistributionResult:
    method:       str
    total_hst:    int
    shareholders: list[Shareholder]
    unallocated:  int   # HST dư do làm tròn


# ─── Phương thức A: Proportional (Tỷ lệ cổ phần) ────────────────────────────
def distribute_proportional(
    shareholders: list[Shareholder],
    total_hst: int = TOTAL_HST,
) -> DistributionResult:
    """
    HST tỷ lệ thuận với số cổ phiếu (shares).
    Phù hợp với biểu quyết cổ phần truyền thống.
    """
    total_shares = sum(s.shares for s in shareholders)
    if total_shares == 0:
        raise ValueError("Tổng cổ phiếu = 0, không thể phân bổ")

    allocated = 0
    result_holders = []

    for s in shareholders:
        ratio = s.shares / total_shares
        hst   = int(total_hst * ratio)
        tier  = _calc_tier(hst, total_hst)
        result_holders.append(Shareholder(
            address=s.address,
            name=s.name,
            shares=s.shares,
            hst=hst,
            tier=tier,
            pct=round(ratio * 100, 2),
        ))
        allocated += hst

    return DistributionResult(
        method="proportional",
        total_hst=total_hst,
        shareholders=result_holders,
        unallocated=total_hst - allocated,
    )


# ─── Phương thức B: Equal (Đồng đều — 1 người 1 phiếu) ───────────────────────
def distribute_equal(
    shareholders: list[Shareholder],
    total_hst: int = TOTAL_HST,
) -> DistributionResult:
    """
    Mỗi cổ đông nhận HST như nhau.
    Phù hợp với bầu cử nhân sự Ban kiểm soát.
    """
    n = len(shareholders)
    if n == 0:
        raise ValueError("Danh sách cổ đông rỗng")

    per_wallet = total_hst // n
    result_holders = []

    for s in shareholders:
        tier = _calc_tier(per_wallet, total_hst)
        result_holders.append(Shareholder(
            address=s.address,
            name=s.name,
            shares=s.shares,
            hst=per_wallet,
            tier=tier,
            pct=round(100 / n, 2),
        ))

    return DistributionResult(
        method="equal",
        total_hst=total_hst,
        shareholders=result_holders,
        unallocated=total_hst - per_wallet * n,
    )


# ─── So sánh voting weight 3 cơ chế ─────────────────────────────────────────
def compare_voting_mechanisms(hst_balances: dict[str, int]) -> dict:
    """
    Tính voting weight theo Linear / Quadratic / Equal.
    Input:  {"Cổ đông A": 4500000, "Cổ đông B": 500000, ...}
    Output: dict với weight và tỷ lệ từng cơ chế
    """
    names    = list(hst_balances.keys())
    balances = list(hst_balances.values())

    linear    = balances[:]
    quadratic = [int(math.sqrt(b)) for b in balances]
    equal     = [1 if b > 0 else 0 for b in balances]

    def pct(weights: list[int]) -> list[float]:
        total = sum(weights)
        if total == 0:
            return [0.0] * len(weights)
        return [round(w / total * 100, 2) for w in weights]

    return {
        "shareholders": names,
        "balances": balances,
        "linear": {
            "weights": linear,
            "pct": pct(linear),
        },
        "quadratic": {
            "weights": quadratic,
            "pct": pct(quadratic),
        },
        "equal": {
            "weights": equal,
            "pct": pct(equal),
        },
    }


# ─── Internal helpers ─────────────────────────────────────────────────────────
def _calc_tier(hst: int, total_hst: int) -> int:
    if total_hst == 0:
        return 0
    ratio = hst / total_hst
    for tier, threshold in sorted(TIER_THRESHOLDS.items(), reverse=True):
        if ratio >= threshold:
            return tier
    return 0


def _print_table(result: DistributionResult) -> None:
    print(f"\n  Phương thức: {result.method.upper()}")
    print(f"  {'Tên':<25} {'Địa chỉ':<14} {'HST':>12} {'%':>7}  {'Tier'}")
    print(f"  {'─'*25} {'─'*14} {'─'*12} {'─'*7}  {'─'*4}")
    for s in result.shareholders:
        short_addr = s.address[:6] + "..." + s.address[-4:] if len(s.address) > 10 else s.address
        tier_label = ["Nhỏ lẻ", "Tổ chức", "Chiến lược", "Sáng lập"][s.tier]
        print(f"  {s.name:<25} {short_addr:<14} {s.hst:>12,} {s.pct:>6.1f}%  {tier_label}")
    print(f"  {'─'*70}")
    print(f"  {'Dư (làm tròn)':<40} {result.unallocated:>12,}")


# ─── Demo chạy trực tiếp ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 70)
    print("  DAO VOTING SYSTEM — Token Distribution Calculator")
    print("=" * 70)

    # Dữ liệu demo từ spec đồ án
    demo_shareholders = [
        Shareholder("0xACCOUNT0", "Chủ tịch HĐQT",      shares=4500),
        Shareholder("0xACCOUNT1", "Quỹ phát triển",      shares=2500),
        Shareholder("0xACCOUNT2", "Cổ đông A (Tổ chức)", shares=1500),
        Shareholder("0xACCOUNT3", "Cổ đông B (Tổ chức)", shares=1000),
        Shareholder("0xACCOUNT4", "Cổ đông C (Nhỏ lẻ)",  shares=500),
    ]

    # ── Proportional ─────────────────────────────────────────────────────────
    prop_result = distribute_proportional(demo_shareholders)
    _print_table(prop_result)

    # ── Equal ─────────────────────────────────────────────────────────────────
    eq_result = distribute_equal(demo_shareholders)
    _print_table(eq_result)

    # ── So sánh 3 cơ chế biểu quyết ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  So sánh Voting Weight — 3 cơ chế")
    print("=" * 70)

    balances = {s.name: s.hst for s in prop_result.shareholders}
    cmp = compare_voting_mechanisms(balances)

    print(f"\n  {'Cổ đông':<25} {'Token':>12}  {'Linear%':>8}  {'Quadratic%':>10}  {'Equal%':>7}")
    print(f"  {'─'*25} {'─'*12}  {'─'*8}  {'─'*10}  {'─'*7}")
    for i, name in enumerate(cmp["shareholders"]):
        print(
            f"  {name:<25} {cmp['balances'][i]:>12,}"
            f"  {cmp['linear']['pct'][i]:>7.1f}%"
            f"  {cmp['quadratic']['pct'][i]:>9.1f}%"
            f"  {cmp['equal']['pct'][i]:>6.1f}%"
        )

    # ── Xuất JSON ─────────────────────────────────────────────────────────────
    out = {
        "proportional": {
            **{k: v for k, v in asdict(prop_result).items() if k != "shareholders"},
            "shareholders": [asdict(s) for s in prop_result.shareholders],
        },
        "equal": {
            **{k: v for k, v in asdict(eq_result).items() if k != "shareholders"},
            "shareholders": [asdict(s) for s in eq_result.shareholders],
        },
        "voting_comparison": cmp,
    }

    out_path = Path(__file__).parent / "distribution_plan.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\n  ✅ Kết quả lưu tại: {out_path}")
    print("=" * 70)
