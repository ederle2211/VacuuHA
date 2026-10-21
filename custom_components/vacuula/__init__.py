from __future__ import annotations

import logging

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_HOST, CONF_PORT
from .hub import VacuulaHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hub = VacuulaHub(
        hass,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
    )

    try:
        robots = await hub.async_get_robots()
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise ConfigEntryNotReady(
            f"Could not read robots from Vacuula server at {hub.base_url}"
        ) from err

    if robots:
        robot_lines = [
            (
                f"- {robot.get('name', 'Unnamed robot')} "
                f"({serial}): {robot.get('type', 'unknown type')}, "
                f"{'online' if robot.get('connected') else 'offline'}"
            )
            for serial, robot in robots.items()
        ]
        robot_list = "\n".join(robot_lines)
    else:
        robot_list = "No robots are registered."

    _LOGGER.info(
        "Robots reported by Vacuula server %s:\n%s",
        hub.base_url,
        robot_list,
    )

    return True