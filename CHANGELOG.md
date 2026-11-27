# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.2] - 2026-11-27

### Added
- New option: **safety margin** (kWh, default 1.0). The charge target is chosen keeping this reserve above the minimum SOC, so a cloudier day or a higher load does not push the house onto mid-peak/peak grid. Reported figures still use the real minimum SOC.
- `safety_margin` plan attribute; reason text for charges made only for the margin.
- New decision `Manter X%`: when the battery is already above the target, it is held there during the window (house runs on off-peak grid) instead of being drained.

## [0.2.1] - 2026-11-23

### Added
- English README and this changelog.
- Card: battery icon with the current SOC in the header; icons on every tile.
- Card: "SOC at window start" tile (e.g. *SOC às 04:00*), the figure the decision is based on.

### Changed
- Card palette aligned with the rest of the dashboard: solar green, grid red, SOC violet, off-peak blue, mid-peak amber, peak rose.
- Card: solar area drawn with a vertical gradient; solar, consumption and SOC drawn as smoothed curves.
- Card: legend split into two fixed rows (series / tariffs).
- Card: charge window is subtle ("janela") when there is no charge and highlighted ("carga → X %") when there is.
- Card: chart 20 % taller.

## [0.2.0] - 2026-11-21

### Added
- Plain-language reason for each decision (`reason` attribute on `sensor.xbattery_pilot_plano`).
- `sensor.xbattery_pilot_rede_prevista` — total grid energy forecast for the next 24 h.
- Forecast accuracy tracking: the day-ahead forecast is stored and compared with the real values (`sensor.xbattery_pilot_desvio_solar_ontem`, `sensor.xbattery_pilot_desvio_consumo_ontem`).
- New option: daily solar production sensor (used for accuracy tracking).
- New plan attributes: `min_soc`, `soc_entity`, `updated_at`, `mode`.
- Card: decision reason, current SOC tile, grid forecast tile, dashed minimum SOC and target SOC lines, "now" marker, footer with yesterday's accuracy, last update and mode.

### Changed
- Card: tariff colours (off-peak blue, mid-peak orange, peak red) so they no longer clash with the SOC line; tariff legend shown as small swatches.
- Card: savings are only shown when the plan charges the battery.

## [0.1.3] - 2026-11-21

### Fixed
- Saturday tariff periods for the Azores weekly cycle, taken from ERSE (no peak on Saturdays).

## [0.1.2] - 2026-11-21

### Added
- Automatic load calibration: real vs. forecast consumption over the last 7 days (factor 0.8–1.3, `load_factor` attribute).

### Changed
- Solar, consumption and cost forecasts always cover a fixed 24 h, from one charge window to the next.
- Sunday is off-peak all day.

## [0.1.1] - 2026-11-21

### Fixed
- Config flow failed to open (number selectors without a unit and with a step below the allowed minimum).
- A setup flow could stay stuck as "already in progress".

## [0.1.0] - 2026-11-21

### Added
- First release (read-only).
- Consumption forecast from long-term statistics, solar forecast from Forecast.Solar / Solcast / Open-Meteo Solar Forecast.
- Half-hourly SOC simulation and target SOC optimisation for EDA tri-hourly tariffs with zero export.
- Sensors for the plan, target SOC, grid charge, forecast cost and savings, solar and consumption forecast, minimum SOC and curtailed solar.
- Lovelace card `custom:xbattery-pilot-card`.

[Unreleased]: https://github.com/BTNBx/xBattery-Pilot/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/BTNBx/xBattery-Pilot/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/BTNBx/xBattery-Pilot/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/BTNBx/xBattery-Pilot/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/BTNBx/xBattery-Pilot/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/BTNBx/xBattery-Pilot/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/BTNBx/xBattery-Pilot/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/BTNBx/xBattery-Pilot/releases/tag/v0.1.0
