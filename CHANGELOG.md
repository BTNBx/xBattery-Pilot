# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- English README and this changelog.

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

[Unreleased]: https://github.com/BTNBx/xBattery-Pilot/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/BTNBx/xBattery-Pilot/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/BTNBx/xBattery-Pilot/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/BTNBx/xBattery-Pilot/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/BTNBx/xBattery-Pilot/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/BTNBx/xBattery-Pilot/releases/tag/v0.1.0
