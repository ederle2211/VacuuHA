from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        VacuulaBatterySensor(coordinator, entry.entry_id, serial, robot)
        for serial, robot in coordinator.data.items()
        if robot.get("type") == "neato.gen3"
    )


class VacuulaBatterySensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True
    _attr_name = "Akku"

    def __init__(
        self,
        coordinator,
        entry_id: str,
        serial: str,
        robot: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._serial = serial
        self._attr_unique_id = f"{entry_id}_{serial}_battery"

        name = robot.get("name") or serial
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{serial}")},
            manufacturer="Neato",
            model="Neato BotVac",
            name=name,
            serial_number=serial,
        )

    @property
    def native_value(self) -> int | None:
        robot = self.coordinator.data.get(self._serial, {})
        status = robot.get("status")
        if not isinstance(status, dict):
            return None

        details = status.get("details")
        charge = details.get("charge") if isinstance(details, dict) else None
        if isinstance(charge, int) and not isinstance(charge, bool):
            return charge
        return None