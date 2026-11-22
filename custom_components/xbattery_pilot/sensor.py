"""Sensores do xBattery Pilot."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import PERCENTAGE, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import XBatteryPilotConfigEntry
from .const import DOMAIN
from .coordinator import XBatteryPilotCoordinator


@dataclass(frozen=True, kw_only=True)
class PlannerSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSORS: tuple[PlannerSensorDescription, ...] = (
    PlannerSensorDescription(
        key="plano",
        name="Plano",
        icon="mdi:battery-clock",
        value_fn=lambda d: d["decision"],
        attr_fn=lambda d: {
            "window_start": d["window_start"],
            "window_end": d["window_end"],
            "horizon_end": d["horizon_end"],
            "load_factor": d["load_factor"],
            "slots": d["rows"],
        },
    ),
    PlannerSensorDescription(
        key="soc_alvo",
        name="SOC alvo",
        icon="mdi:battery-charging-high",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d["target_soc"],
    ),
    PlannerSensorDescription(
        key="carga_rede",
        name="Carga pela rede",
        icon="mdi:transmission-tower-import",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d["grid_charge"],
    ),
    PlannerSensorDescription(
        key="custo_previsto",
        name="Custo previsto",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="EUR",
        value_fn=lambda d: d["cost"],
    ),
    PlannerSensorDescription(
        key="poupanca_prevista",
        name="Poupança prevista",
        icon="mdi:piggy-bank-outline",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="EUR",
        value_fn=lambda d: d["savings"],
    ),
    PlannerSensorDescription(
        key="solar_previsto",
        name="Solar previsto",
        icon="mdi:solar-power-variant",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d["pv_forecast"],
    ),
    PlannerSensorDescription(
        key="consumo_previsto",
        name="Consumo previsto",
        icon="mdi:home-lightning-bolt-outline",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d["load_forecast"],
    ),
    PlannerSensorDescription(
        key="soc_inicio_carga",
        name="SOC no início da carga",
        icon="mdi:battery-arrow-down-outline",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d["soc_window_start"],
    ),
    PlannerSensorDescription(
        key="soc_minimo_previsto",
        name="SOC mínimo previsto",
        icon="mdi:battery-low",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d["soc_min"],
    ),
    PlannerSensorDescription(
        key="solar_desperdicado",
        name="Solar desperdiçado",
        icon="mdi:solar-power-variant-outline",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d["curtailed"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XBatteryPilotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(PlannerSensor(coordinator, entry, desc) for desc in SENSORS)


class PlannerSensor(CoordinatorEntity[XBatteryPilotCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({"slots"})
    entity_description: PlannerSensorDescription

    def __init__(
        self,
        coordinator: XBatteryPilotCoordinator,
        entry: XBatteryPilotConfigEntry,
        description: PlannerSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="xBattery Pilot",
            manufacturer="BTNBx",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.coordinator.data)
