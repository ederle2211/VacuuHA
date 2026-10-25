from __future__ import annotations

from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
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
        VacuulaVacuum(coordinator, entry.entry_id, serial, robot)
        for serial, robot in coordinator.data.items()
        if robot.get("type") == "neato.gen3"
    )


class VacuulaVacuum(CoordinatorEntity, StateVacuumEntity):
    _attr_supported_features = VacuumEntityFeature.STATE

    def __init__(
        self,
        coordinator,
        entry_id: str,
        serial: str,
        robot: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._serial = serial

        name = robot.get("name") or serial
        self._attr_unique_id = f"{entry_id}_{serial}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{serial}")},
            manufacturer="Neato",
            model="Neato BotVac",
            name=name,
            serial_number=serial,
        )

    @property
    def _robot(self) -> dict[str, Any]:
        return self.coordinator.data.get(self._serial, {})

    @property
    def available(self) -> bool:
        return (
            super().available
            and self._robot.get("connected", False)
            and isinstance(self._robot.get("status"), dict)
        )

    @property
    def activity(self) -> VacuumActivity | None:
        status = self._robot.get("status")
        if not isinstance(status, dict):
            return None

        state = status.get("state")
        action = status.get("action")
        details = status.get("details") or {}

        if state == 4:
            return VacuumActivity.ERROR
        if state == 3:
            return VacuumActivity.PAUSED
        if state == 1:
            return (
                VacuumActivity.DOCKED
                if details.get("isDocked")
                else VacuumActivity.IDLE
            )
        if state == 2 and action == 4:
            return VacuumActivity.RETURNING
        if state == 2:
            return VacuumActivity.CLEANING

        return None

    @property
    def battery_level(self) -> int | None:
        status = self._robot.get("status")
        if not isinstance(status, dict):
            return None

        charge = (status.get("details") or {}).get("charge")
        return charge if isinstance(charge, int) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        status = self._robot.get("status")
        if not isinstance(status, dict):
            return {"serial": self._serial}

        details = status.get("details") or {}
        return {
            "serial": self._serial,
            "model": (status.get("meta") or {}).get("modelName"),
            "firmware": (status.get("meta") or {}).get("firmware"),
            "is_charging": details.get("isCharging"),
            "is_docked": details.get("isDocked"),
            "available_commands": status.get("availableCommands"),
        }