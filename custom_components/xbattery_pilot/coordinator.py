"""xBattery Pilot coordinator."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CAPACITY,
    CONF_CHARGE_END,
    CONF_CHARGE_POWER,
    CONF_CHARGE_START,
    CONF_FORECAST_ENTRY,
    CONF_LOAD_SENSOR,
    CONF_MIN_SOC,
    CONF_PRICE_CHEIAS,
    CONF_PRICE_PONTA,
    CONF_PRICE_VAZIO,
    CONF_PV_ENERGY_SENSOR,
    CONF_PV_SCALING,
    CONF_SAFETY_MARGIN,
    CONF_SOC_SENSOR,
    CALIBRATION_DAYS,
    DEFAULT_LOAD_W,
    DEFAULTS,
    DOMAIN,
    EFF_CHARGE,
    EFF_DISCHARGE,
    HISTORY_DAYS,
    LOAD_FACTOR_MAX,
    LOAD_FACTOR_MIN,
    STORAGE_VERSION,
    TARGET_STEP,
    UPDATE_MINUTES,
)
from .planner import Battery, SimResult, Slot, optimise, simulate
from .tariff import CHEIAS, PONTA, VAZIO, period_at

_LOGGER = logging.getLogger(__name__)
SLOT = timedelta(minutes=30)

type HourKey = tuple[Any, int]


def _parse_time(value: str) -> time:
    parts = str(value).split(":")
    return time(int(parts[0]), int(parts[1]))


def _forecast_load(hist: dict[HourKey, float], t: datetime) -> float:
    """Forecast mean load (W) for the hour of t."""
    return _forecast_load_at(hist, t.date(), t.hour)


def _forecast_load_at(hist: dict[HourKey, float], d: Any, h: int) -> float:
    """Forecast mean load (W) for day d, hour h (uses previous days only)."""
    recent = [
        hist[k] for i in range(1, 8) if (k := (d - timedelta(days=i), h)) in hist
    ]
    parts: list[tuple[float, float]] = []
    if recent:
        parts.append((sum(recent) / len(recent), 0.5))
    for days, weight in ((7, 0.25), (14, 0.25)):
        k = (d - timedelta(days=days), h)
        if k in hist:
            parts.append((hist[k], weight))
    if not parts:
        return DEFAULT_LOAD_W
    return max(0.0, sum(v * w for v, w in parts) / sum(w for _, w in parts))


def _load_factor(hist: dict[HourKey, float], today: Any) -> float:
    """Correction factor: actual / forecast load over the last complete days."""
    actual = predicted = 0.0
    for i in range(1, CALIBRATION_DAYS + 1):
        d = today - timedelta(days=i)
        for h in range(24):
            if (d, h) in hist:
                actual += hist[(d, h)]
                predicted += _forecast_load_at(hist, d, h)
    if actual <= 0 or predicted <= 0:
        return 1.0
    return min(max(actual / predicted, LOAD_FACTOR_MIN), LOAD_FACTOR_MAX)


def _deviation(pred: float | None, real: float | None) -> int | None:
    """Forecast deviation in % of the actual value (negative = under-forecast)."""
    if pred is None or real is None or real < 0.1:
        return None
    return round((pred - real) / real * 100)


def _peak_import_kwh(slots: list[Slot], rows: list[dict[str, Any]], ws: datetime, vazio: float) -> float:
    return sum(
        r["grid"] for s, r in zip(slots, rows) if s.start >= ws and s.price > vazio + 1e-9
    ) / 1000


# Text shown in the plan state and reason. Portuguese is used when Home
# Assistant is set to Portuguese; English otherwise.
TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "no_charge": "No charge",
        "hold": "Hold {target}%",
        "charge": "Charge to {target}%",
        "hold_reason": "Safety reserve — holds the battery at {target}% during the window and runs the house on off-peak grid",
        "margin_reason": "Safety charge — keeps {margin} kWh of reserve above the minimum",
        "avoid_reason": "Avoids {kwh} kWh of mid-peak/peak grid",
        "covered_reason": "Solar and battery cover the load",
        "offpeak_reason": "All grid needed is off-peak — charging does not pay off",
        "solar_reason": "Charging does not pay off — forecast solar fills the battery",
    },
    "pt": {
        "no_charge": "Sem carga",
        "hold": "Manter {target}%",
        "charge": "Carregar até {target}%",
        "hold_reason": "Reserva de segurança — segura a bateria em {target}% na janela e usa a rede em vazio",
        "margin_reason": "Carga de segurança — mantém {margin} kWh de reserva acima do mínimo",
        "avoid_reason": "Evita {kwh} kWh de rede em cheias/ponta",
        "covered_reason": "Solar e bateria cobrem o consumo",
        "offpeak_reason": "A rede necessária é toda em vazio — carregar não compensa",
        "solar_reason": "Carregar não compensa — o solar previsto enche a bateria",
    },
}


def _texts(language: str | None) -> tuple[dict[str, str], str]:
    """Return (texts, decimal separator) for the Home Assistant language."""
    if (language or "").lower().startswith("pt"):
        return TEXTS["pt"], ","
    return TEXTS["en"], "."


def _fmt(value: float, sep: str) -> str:
    return f"{value:.1f}".replace(".", sep)


def _decision(best: SimResult, language: str | None = None) -> str:
    t, _ = _texts(language)
    if not best.target_soc:
        return t["no_charge"]
    if best.charge_wh < 50:
        return t["hold"].format(target=best.target_soc)
    return t["charge"].format(target=best.target_soc)


def _reason(
    best: SimResult,
    base: SimResult,
    slots: list[Slot],
    ws: datetime,
    vazio: float,
    grid_kwh: float,
    margin_kwh: float = 0.0,
    language: str | None = None,
) -> str:
    """Short explanation of the decision."""
    t, sep = _texts(language)
    best_peak = _peak_import_kwh(slots, best.rows, ws, vazio)
    if best.target_soc:
        avoided = _peak_import_kwh(slots, base.rows, ws, vazio) - best_peak
        if best.charge_wh < 50:
            return t["hold_reason"].format(target=best.target_soc)
        if avoided < 0.05 and margin_kwh > 0:
            return t["margin_reason"].format(margin=_fmt(margin_kwh, sep))
        return t["avoid_reason"].format(kwh=_fmt(avoided, sep))
    if grid_kwh < 0.05:
        return t["covered_reason"]
    if best_peak < 0.05:
        return t["offpeak_reason"]
    return t["solar_reason"]


class XBatteryPilotCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Computes the charge plan."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_MINUTES),
        )
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.previsoes"
        )
        self._pred: dict[str, dict[str, float]] | None = None

    @property
    def cfg(self) -> dict[str, Any]:
        return {**DEFAULTS, **self.entry.data, **self.entry.options}

    def _window(self, now: datetime, cfg: dict[str, Any]) -> tuple[datetime, datetime]:
        s = _parse_time(cfg[CONF_CHARGE_START])
        e = _parse_time(cfg[CONF_CHARGE_END])
        ws = now.replace(hour=s.hour, minute=s.minute, second=0, microsecond=0)
        we = now.replace(hour=e.hour, minute=e.minute, second=0, microsecond=0)
        if we <= ws:
            we += timedelta(days=1)
        if ws - timedelta(days=1) <= now < we - timedelta(days=1):
            return ws - timedelta(days=1), we - timedelta(days=1)
        if now >= we:
            ws += timedelta(days=1)
            we += timedelta(days=1)
        return ws, we

    async def _pv_forecast(self, cfg: dict[str, Any]) -> dict[HourKey, float]:
        entry_id = cfg.get(CONF_FORECAST_ENTRY)
        fentry = self.hass.config_entries.async_get_entry(entry_id) if entry_id else None
        if fentry is None:
            raise UpdateFailed("Solar forecast integration not found")
        integration = await async_get_integration(self.hass, fentry.domain)
        platform = await integration.async_get_platform("energy")
        data = await platform.async_get_solar_forecast(self.hass, entry_id)
        if not data or not data.get("wh_hours"):
            raise UpdateFailed("Solar forecast is empty")
        out: dict[HourKey, float] = {}
        for ts, wh in data["wh_hours"].items():
            parsed = dt_util.parse_datetime(ts)
            if parsed is None:
                continue
            local = dt_util.as_local(parsed)
            key = (local.date(), local.hour)
            out[key] = out.get(key, 0.0) + float(wh)
        return out

    async def _load_history(self, cfg: dict[str, Any], now: datetime) -> dict[HourKey, float]:
        sid = cfg[CONF_LOAD_SENSOR]
        start = dt_util.start_of_local_day(now) - timedelta(days=CALIBRATION_DAYS + 15)
        stats = await get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            start,
            now,
            {sid},
            "hour",
            None,
            {"mean"},
        )
        out: dict[HourKey, float] = {}
        for row in stats.get(sid, []):
            st = row["start"]
            if isinstance(st, (int, float)):
                st = dt_util.utc_from_timestamp(st)
            st = dt_util.as_local(st)
            if row.get("mean") is not None:
                out[(st.date(), st.hour)] = max(0.0, float(row["mean"]))
        if not out:
            raise UpdateFailed(f"No statistics for {sid}")
        return out

    async def _pv_actual_kwh(self, cfg: dict[str, Any], day: date) -> float | None:
        sid = cfg.get(CONF_PV_ENERGY_SENSOR)
        if not sid:
            return None
        start = dt_util.start_of_local_day(day)
        end = start + timedelta(days=1)
        stats = await get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            start,
            end,
            {sid},
            "hour",
            None,
            {"change"},
        )
        rows = stats.get(sid, [])
        if not rows:
            return None
        return sum(max(float(r.get("change") or 0), 0.0) for r in rows)

    async def _track_accuracy(
        self,
        cfg: dict[str, Any],
        today: date,
        pv: dict[HourKey, float],
        scaling: float,
        load_hist: dict[HourKey, float],
        load_factor: float,
    ) -> tuple[int | None, int | None]:
        """Store tomorrow's forecast and compare yesterday's with the actual values."""
        if self._pred is None:
            data = await self._store.async_load()
            self._pred = (data or {}).get("pred", {})

        tomorrow = today + timedelta(days=1)
        pv_day = sum(v for (d, _), v in pv.items() if d == tomorrow) * scaling
        if pv_day > 0:
            load_day = sum(_forecast_load_at(load_hist, tomorrow, h) for h in range(24)) * load_factor
            self._pred[tomorrow.isoformat()] = {
                "pv": round(pv_day / 1000, 3),
                "load": round(load_day / 1000, 3),
            }
        oldest = today - timedelta(days=HISTORY_DAYS)
        self._pred = {k: v for k, v in self._pred.items() if date.fromisoformat(k) >= oldest}
        self._store.async_delay_save(lambda: {"pred": self._pred}, 60)

        yesterday = today - timedelta(days=1)
        pred_y = self._pred.get(yesterday.isoformat())
        if not pred_y:
            return None, None
        hours = [load_hist[(yesterday, h)] for h in range(24) if (yesterday, h) in load_hist]
        real_load = sum(hours) / 1000 if len(hours) >= 20 else None
        real_pv = await self._pv_actual_kwh(cfg, yesterday)
        return _deviation(pred_y["pv"], real_pv), _deviation(pred_y["load"], real_load)

    async def _async_update_data(self) -> dict[str, Any]:
        cfg = self.cfg
        now = dt_util.now()

        state = self.hass.states.get(cfg[CONF_SOC_SENSOR])
        try:
            soc_pct = float(state.state)  # type: ignore[union-attr]
        except (AttributeError, TypeError, ValueError) as err:
            raise UpdateFailed(f"SOC unavailable: {cfg[CONF_SOC_SENSOR]}") from err

        ws, we = self._window(now, cfg)
        horizon_end = ws + timedelta(days=1)
        pv = await self._pv_forecast(cfg)
        load_hist = await self._load_history(cfg, now)

        prices = {
            VAZIO: float(cfg[CONF_PRICE_VAZIO]),
            CHEIAS: float(cfg[CONF_PRICE_CHEIAS]),
            PONTA: float(cfg[CONF_PRICE_PONTA]),
        }
        scaling = float(cfg[CONF_PV_SCALING])
        load_factor = _load_factor(load_hist, now.date())

        slots: list[Slot] = []
        t = now.replace(minute=(now.minute // 30) * 30, second=0, microsecond=0)
        while t < horizon_end:
            t_end = t + SLOT
            hours = (t_end - max(t, now)).total_seconds() / 3600
            if hours > 0:
                slots.append(
                    Slot(
                        start=t,
                        hours=hours,
                        pv_wh=pv.get((t.date(), t.hour), 0.0) * hours * scaling,
                        load_wh=_forecast_load(load_hist, t) * load_factor * hours,
                        price=prices[period_at(t)],
                        in_window=ws <= t < we,
                    )
                )
            t = t_end

        bat = Battery(
            capacity_wh=float(cfg[CONF_CAPACITY]),
            min_soc=float(cfg[CONF_MIN_SOC]),
            charge_power_w=float(cfg[CONF_CHARGE_POWER]),
            eff_charge=EFF_CHARGE,
            eff_discharge=EFF_DISCHARGE,
        )
        margin_kwh = float(cfg.get(CONF_SAFETY_MARGIN, 0.0) or 0.0)
        best, base = optimise(
            slots,
            soc_pct / 100 * bat.capacity_wh,
            bat,
            prices[VAZIO],
            TARGET_STEP,
            margin_wh=margin_kwh * 1000,
        )
        cap = bat.capacity_wh
        base = simulate(
            slots, soc_pct / 100 * bat.capacity_wh, bat, 0, prices[VAZIO], keep_rows=True
        )
        acc_pv, acc_load = await self._track_accuracy(
            cfg, now.date(), pv, scaling, load_hist, load_factor
        )

        def pct(wh: float | None) -> float | None:
            return None if wh is None else round(wh / cap * 100, 1)

        # Reported metrics: from the next charge window to the following one (fixed 24 h)
        plan_slots = [s for s in slots if s.start >= ws]
        plan_cost = sum(
            r["grid"] / 1000 * s.price
            for s, r in zip(slots, best.rows)
            if s.start >= ws
        )
        grid_kwh = sum(r["grid"] for s, r in zip(slots, best.rows) if s.start >= ws) / 1000

        return {
            "decision": _decision(best, self.hass.config.language),
            "target_soc": best.target_soc,
            "grid_charge": round(best.charge_wh / 1000, 2),
            "cost": round(plan_cost, 2),
            "savings": round(max(base.score - best.score, 0.0), 2),
            "pv_forecast": round(sum(s.pv_wh for s in plan_slots) / 1000, 2),
            "load_forecast": round(sum(s.load_wh for s in plan_slots) / 1000, 2),
            "load_factor": round(load_factor, 3),
            "soc_window_start": pct(best.soc_window_start_wh),
            "soc_min": pct(best.soc_min_wh),
            "curtailed": round(best.curtailed_wh / 1000, 2),
            "window_start": ws.isoformat(),
            "window_end": we.isoformat(),
            "horizon_end": horizon_end.isoformat(),
            "grid_forecast": round(grid_kwh, 2),
            "reason": _reason(
                best, base, slots, ws, prices[VAZIO], grid_kwh, margin_kwh, self.hass.config.language
            ),
            "safety_margin": margin_kwh,
            "acc_pv": acc_pv,
            "acc_load": acc_load,
            "min_soc": float(cfg[CONF_MIN_SOC]),
            "soc_entity": cfg[CONF_SOC_SENSOR],
            "updated_at": now.isoformat(),
            "mode": "read_only",
            "rows": best.rows,
        }
