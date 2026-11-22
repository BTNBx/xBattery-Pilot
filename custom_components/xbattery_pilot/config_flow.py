"""Config flow do xBattery Pilot."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

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
    CONF_SOC_SENSOR,
    DEFAULTS,
    DOMAIN,
    FORECAST_DOMAINS,
)


def _num(mn: float, mx: float, step: float | str, unit: str | None = None) -> selector.NumberSelector:
    config = selector.NumberSelectorConfig(
        min=mn, max=mx, step=step, mode=selector.NumberSelectorMode.BOX
    )
    if unit:
        config["unit_of_measurement"] = unit
    return selector.NumberSelector(config)


def _forecast_options(hass: HomeAssistant) -> list[selector.SelectOptionDict]:
    return [
        selector.SelectOptionDict(value=e.entry_id, label=f"{e.title} ({e.domain})")
        for d in FORECAST_DOMAINS
        for e in hass.config_entries.async_entries(d)
    ]


def _schema(hass: HomeAssistant, d: dict[str, Any]) -> vol.Schema:
    options = _forecast_options(hass)
    forecast_default = d.get(CONF_FORECAST_ENTRY) or (
        options[0]["value"] if options else vol.UNDEFINED
    )
    sensor_sel = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
    return vol.Schema(
        {
            vol.Required(CONF_SOC_SENSOR, default=d[CONF_SOC_SENSOR]): sensor_sel,
            vol.Required(CONF_LOAD_SENSOR, default=d[CONF_LOAD_SENSOR]): sensor_sel,
            vol.Required(CONF_PV_ENERGY_SENSOR, default=d[CONF_PV_ENERGY_SENSOR]): sensor_sel,
            vol.Required(CONF_FORECAST_ENTRY, default=forecast_default): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options)
            ),
            vol.Required(CONF_PV_SCALING, default=d[CONF_PV_SCALING]): _num(0.1, 3, 0.05),
            vol.Required(CONF_CAPACITY, default=d[CONF_CAPACITY]): _num(1000, 100000, 10, "Wh"),
            vol.Required(CONF_MIN_SOC, default=d[CONF_MIN_SOC]): _num(0, 100, 1, "%"),
            vol.Required(CONF_CHARGE_START, default=d[CONF_CHARGE_START]): selector.TimeSelector(),
            vol.Required(CONF_CHARGE_END, default=d[CONF_CHARGE_END]): selector.TimeSelector(),
            vol.Required(CONF_CHARGE_POWER, default=d[CONF_CHARGE_POWER]): _num(100, 20000, 50, "W"),
            vol.Required(CONF_PRICE_VAZIO, default=d[CONF_PRICE_VAZIO]): _num(0, 2, "any", "€/kWh"),
            vol.Required(CONF_PRICE_CHEIAS, default=d[CONF_PRICE_CHEIAS]): _num(0, 2, "any", "€/kWh"),
            vol.Required(CONF_PRICE_PONTA, default=d[CONF_PRICE_PONTA]): _num(0, 2, "any", "€/kWh"),
        }
    )


class XBatteryPilotConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not _forecast_options(self.hass):
            return self.async_abort(reason="no_forecast")
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="xBattery Pilot", data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema(self.hass, DEFAULTS))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return XBatteryPilotOptionsFlow()


class XBatteryPilotOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = {**DEFAULTS, **self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(self.hass, current))
