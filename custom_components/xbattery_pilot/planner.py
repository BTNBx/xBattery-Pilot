"""Simulation and optimisation of the overnight charge."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any


@dataclass
class Slot:
    start: datetime
    hours: float
    pv_wh: float
    load_wh: float
    price: float
    in_window: bool


@dataclass
class Battery:
    capacity_wh: float
    min_soc: float
    charge_power_w: float
    eff_charge: float
    eff_discharge: float


@dataclass
class SimResult:
    target_soc: int
    import_cost: float
    score: float
    import_wh: float
    charge_wh: float
    curtailed_wh: float
    soc_end_wh: float
    soc_min_wh: float
    soc_window_start_wh: float | None
    rows: list[dict[str, Any]] = field(default_factory=list)


def simulate(
    slots: list[Slot],
    soc_wh: float,
    bat: Battery,
    target_soc: int,
    terminal_price: float,
    keep_rows: bool = False,
) -> SimResult:
    """Simulate SOC slot by slot for a target SOC (0 = no grid charge)."""
    cap = bat.capacity_wh
    floor = cap * bat.min_soc / 100
    target_wh = cap * target_soc / 100
    soc = min(max(soc_wh, 0.0), cap)
    cost = imp_total = charge_total = curtailed = 0.0
    soc_min = soc
    soc_ws: float | None = None
    rows: list[dict[str, Any]] = []

    for s in slots:
        net = s.pv_wh - s.load_wh
        imp = 0.0
        grid_charge = 0.0
        charging = s.in_window and target_soc > 0

        if s.in_window and soc_ws is None:
            soc_ws = soc

        if charging and soc < target_wh:
            need_in = (target_wh - soc) / bat.eff_charge
            pv_surplus = max(net, 0.0)
            imp = max(-net, 0.0)
            pv_used = min(pv_surplus, need_in)
            grid_charge = min(max(need_in - pv_used, 0.0), bat.charge_power_w * s.hours)
            soc += (pv_used + grid_charge) * bat.eff_charge
            extra = pv_surplus - pv_used
            if extra > 0:
                add = min(extra * bat.eff_charge, cap - soc)
                soc += add
                curtailed += extra - add / bat.eff_charge
            imp += grid_charge
        else:
            fl = max(floor, target_wh) if charging else floor
            if net >= 0:
                add = min(net * bat.eff_charge, cap - soc)
                soc += add
                curtailed += net - add / bat.eff_charge
            else:
                deficit = -net
                avail = max(soc - fl, 0.0) * bat.eff_discharge
                use = min(deficit, avail)
                soc -= use / bat.eff_discharge
                imp = deficit - use

        cost += imp / 1000 * s.price
        imp_total += imp
        charge_total += grid_charge
        soc_min = min(soc_min, soc)

        if keep_rows:
            rows.append(
                {
                    "t": s.start.isoformat(),
                    "pv": round(s.pv_wh),
                    "load": round(s.load_wh),
                    "grid": round(imp),
                    "soc": round(soc / cap * 100, 1),
                    "price": s.price,
                }
            )

    terminal = max(soc - floor, 0.0) / 1000 * bat.eff_discharge * terminal_price
    return SimResult(
        target_soc=target_soc,
        import_cost=cost,
        score=cost - terminal,
        import_wh=imp_total,
        charge_wh=charge_total,
        curtailed_wh=curtailed,
        soc_end_wh=soc,
        soc_min_wh=soc_min,
        soc_window_start_wh=soc_ws,
        rows=rows,
    )


def optimise(
    slots: list[Slot],
    soc_wh: float,
    bat: Battery,
    terminal_price: float,
    step: int = 5,
    margin_wh: float = 0.0,
) -> tuple[SimResult, SimResult]:
    """Return (best plan, no-charge plan).

    The target SOC is chosen keeping a safety reserve (margin_wh) above the
    minimum SOC; the returned results are simulated with the real minimum SOC.
    """
    plan_min = min(bat.min_soc + max(margin_wh, 0.0) / bat.capacity_wh * 100, 100.0)
    plan_bat = replace(bat, min_soc=plan_min)
    best = simulate(slots, soc_wh, plan_bat, 0, terminal_price)
    start = int(math.ceil(plan_min / step) * step)
    for target in range(start, 101, step):
        res = simulate(slots, soc_wh, plan_bat, target, terminal_price)
        if res.score < best.score - 0.005:
            best = res
    base = simulate(slots, soc_wh, bat, 0, terminal_price)
    best = simulate(slots, soc_wh, bat, best.target_soc, terminal_price, keep_rows=True)
    return best, base
