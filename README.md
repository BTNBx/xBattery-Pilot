# xBattery Pilot

A Home Assistant custom integration that plans the overnight grid charge of a home battery (Deye hybrid inverters) from the solar forecast, your own consumption history and time-of-use tariffs.

It answers one question every night: **how far should the battery be charged from the grid in the cheap window so that tomorrow costs the least?**

> **v0.2 - read-only.** The plan is calculated and exposed as sensors; the inverter is not controlled yet.

## Features

- **Consumption forecast** from Home Assistant long-term statistics of your load sensor (weighted average of the last 7 days and of the same weekday 7 and 14 days ago)
- **Automatic load calibration** - compares real vs. forecast consumption over the last 7 days and corrects the forecast (factor clamped to 0.8–1.3)
- **Solar forecast** from Forecast.Solar, Solcast or Open-Meteo Solar Forecast (any integration that feeds the Energy dashboard)
- **SOC simulation** in 30-minute steps with charge/discharge efficiency, minimum SOC and grid-charge power limits
- **Cost optimisation** — picks the target SOC (5 % steps) that minimises the cost of grid energy across off-peak / mid-peak / peak periods, built for **zero-export** systems (surplus solar is curtailed, not sold)
- **Plain-language reason** for every decision (e.g. *"Evita 3,1 kWh de rede em cheias/ponta"* - avoids 3.1 kWh of grid in mid-peak/peak)
- **Forecast accuracy tracking** - stores the day-ahead forecast and reports yesterday's solar and consumption deviation
- **Lovelace card** with the plan chart, tariff strip, target and minimum SOC lines

## Requirements

- Home Assistant 2024.12 or newer
- A battery SOC sensor (%) and a house load power sensor (W) with `state_class: measurement` (e.g. from the Solarman / Deye integration)
- One solar forecast integration: **Forecast.Solar**, **Solcast** or **Open-Meteo Solar Forecast**
- Optional: a daily solar production sensor (kWh) for accuracy tracking

## Installation

### HACS / Marketplace

1. HACS (Marketplace on HA 2026.11+) → ⋮ → **Custom repositories** → `https://github.com/BTNBx/xBattery-Pilot`, category **Integration**
2. Install **xBattery Pilot** and restart Home Assistant
3. **Settings → Devices & services → Add integration → xBattery Pilot**

### Manual

Copy `custom_components/xbattery_pilot` into your `config/custom_components/` folder and restart Home Assistant.

## Configuration

All options are set in the UI and can be changed later under **Configure**.

| Option | Default | Description |
|---|---|---|
| Battery SOC sensor | `sensor.deye_battery` | Battery state of charge (%) |
| House load sensor | `sensor.deye_load_l1_power` | House consumption (W), used for the forecast |
| Daily solar production sensor | `sensor.deye_today_production` | Daily PV energy (kWh), used for accuracy tracking |
| Solar forecast | — | Your forecast integration |
| Solar correction factor | `1.0` | Scales the solar forecast up or down |
| Battery capacity | `10240` Wh | Usable capacity |
| Minimum SOC | `20` % | The battery is never planned below this |
| Charge window start / end | `04:00` / `08:00` | When grid charging is allowed |
| Grid charge power | `2000` W | Maximum charge power from the grid |
| Off-peak / mid-peak / peak price | `0.1082` / `0.1681` / `0.2584` €/kWh | Energy prices per period |

### Tariff periods

The built-in schedule is the **EDA (Azores) BTN tri-hourly weekly cycle** published by ERSE:

| Day | Winter (Nov–May) | Summer (Jun–Oct) |
|---|---|---|
| Weekdays | off-peak 00:00–07:00 · peak 18:30–21:30 · mid-peak the rest | off-peak 00:00–07:00 · peak 10:30–15:30 · mid-peak the rest |
| Saturday | mid-peak 11:30–13:30 and 18:00–23:00 · off-peak the rest | mid-peak 11:00–14:30 and 19:30–23:00 · off-peak the rest |
| Sunday | off-peak all day | off-peak all day |

Other schedules can be set by editing `tariff.py`.

## Entities

| Entity | Description |
|---|---|
| `sensor.xbattery_pilot_plano` | Decision (`Carregar até X%` / `Sem carga`). Attributes: reason, charge window, load factor, minimum SOC, half-hourly plan (`slots`) |
| `sensor.xbattery_pilot_soc_alvo` | Target SOC (%) — `0` when no charge is needed |
| `sensor.xbattery_pilot_carga_pela_rede` | Energy charged from the grid (kWh) |
| `sensor.xbattery_pilot_rede_prevista` | Total grid energy forecast for the next 24 h (kWh) |
| `sensor.xbattery_pilot_custo_previsto` | Forecast grid cost for the next 24 h (€) |
| `sensor.xbattery_pilot_poupanca_prevista` | Savings vs. not charging (€) |
| `sensor.xbattery_pilot_solar_previsto` | Solar forecast for the next 24 h (kWh) |
| `sensor.xbattery_pilot_consumo_previsto` | Consumption forecast for the next 24 h (kWh) |
| `sensor.xbattery_pilot_soc_no_inicio_da_carga` | Forecast SOC when the charge window opens (%) |
| `sensor.xbattery_pilot_soc_minimo_previsto` | Lowest forecast SOC (%) |
| `sensor.xbattery_pilot_solar_desperdicado` | Solar that would be curtailed (kWh) |
| `sensor.xbattery_pilot_desvio_solar_ontem` | Yesterday's solar forecast deviation (%) |
| `sensor.xbattery_pilot_desvio_consumo_ontem` | Yesterday's consumption forecast deviation (%) |

Entity names, states and the card are currently in Portuguese; an English translation is planned.

The 24 h figures always cover one charge window to the next (e.g. 04:00 → 04:00). The plan is recalculated every 15 minutes.

## Lovelace card

The card lives in `dist/xbattery-pilot-card.js`.

1. Add it as a dashboard resource (**Settings → Dashboards → ⋮ → Resources**), type **JavaScript module**, either:
   - `https://cdn.jsdelivr.net/gh/BTNBx/xBattery-Pilot@main/dist/xbattery-pilot-card.js`, or
   - copy the file to `config/www/` and use `/local/xbattery-pilot-card.js`
2. Add the card:

```yaml
type: custom:xbattery-pilot-card
```

| Option | Default | Description |
|---|---|---|
| `prefix` | `sensor.xbattery_pilot_` | Entity prefix |
| `title` | `xBattery Pilot` | Card title |

Drag across the chart to see solar, consumption, grid, SOC and tariff for each half hour.

## How it works

1. Reads up to 22 days of hourly load statistics and builds an hourly consumption forecast, corrected by the calibration factor.
2. Reads the hourly solar forecast.
3. Simulates the battery from now until the window after next, for every target SOC from the minimum to 100 %.
4. Keeps the cheapest plan; leftover battery energy at the end is credited so the planner does not drain the battery just to look cheaper.

## Roadmap

- Inverter control (Deye time-of-use programme via Solarman)
- Peak shaving awareness
- Flexible loads (e.g. dehumidifiers) on solar surplus
- Configurable tariff schedules in the UI
- English translation of states and card

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Disclaimer

Use at your own risk. While in read-only mode the integration never writes to the inverter.
