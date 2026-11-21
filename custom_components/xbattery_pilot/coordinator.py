"""Coordinator do xBattery Pilot."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
    CONF_PV_SCALING,
    CONF_SOC_SENSOR,
    DEFAULT_LOAD_W,
    DEFAULTS,
    DOMAIN,
    EFF_CHARGE,
    EFF_DISCHARGE,
    TARGET_STEP,
    UPDATE_MINUTES,
)
from .planner import Battery, Slot, optimise
from .tariff import CHEIAS, PONTA, VAZIO, period_at

_LOGGER = logging.getLogger(__name__)
SLOT = timedelta(minutes=30)

type HourKey = tuple[Any, int]


def _parse_time(value: str) -> time:
    parts = str(value).split(":")
    return time(int(parts[0]), int(parts[1]))


def _forecast_load(hist: dict[HourKey, float], t: datetime) -> float:
    """Consumo médio previsto (W) para a hora de t."""
    d, h = t.date(), t.hour
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


class XBatteryPilotCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Calcula o plano de carga."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_MINUTES),
        )
        self.entry = entry

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
            raise UpdateFailed("Integração de previsão solar não encontrada")
        integration = await async_get_integration(self.hass, fentry.domain)
        platform = await integration.async_get_platform("energy")
        data = await platform.async_get_solar_forecast(self.hass, entry_id)
        if not data or not data.get("wh_hours"):
            raise UpdateFailed("Previsão solar vazia")
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
        start = dt_util.start_of_local_day(now) - timedelta(days=15)
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
            raise UpdateFailed(f"Sem estatísticas para {sid}")
        return out

    async def _async_update_data(self) -> dict[str, Any]:
        cfg = self.cfg
        now = dt_util.now()

        state = self.hass.states.get(cfg[CONF_SOC_SENSOR])
        try:
            soc_pct = float(state.state)  # type: ignore[union-attr]
        except (AttributeError, TypeError, ValueError) as err:
            raise UpdateFailed(f"SOC indisponível: {cfg[CONF_SOC_SENSOR]}") from err

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
                        load_wh=_forecast_load(load_hist, t) * hours,
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
        best, base = optimise(
            slots, soc_pct / 100 * bat.capacity_wh, bat, prices[VAZIO], TARGET_STEP
        )
        cap = bat.capacity_wh

        def pct(wh: float | None) -> float | None:
            return None if wh is None else round(wh / cap * 100, 1)

        return {
            "decision": f"Carregar até {best.target_soc}%" if best.target_soc else "Sem carga",
            "target_soc": best.target_soc,
            "grid_charge": round(best.charge_wh / 1000, 2),
            "cost": round(best.import_cost, 2),
            "savings": round(max(base.score - best.score, 0.0), 2),
            "pv_forecast": round(sum(s.pv_wh for s in slots) / 1000, 2),
            "load_forecast": round(sum(s.load_wh for s in slots) / 1000, 2),
            "soc_window_start": pct(best.soc_window_start_wh),
            "soc_min": pct(best.soc_min_wh),
            "curtailed": round(best.curtailed_wh / 1000, 2),
            "window_start": ws.isoformat(),
            "window_end": we.isoformat(),
            "horizon_end": horizon_end.isoformat(),
            "rows": best.rows,
        }
