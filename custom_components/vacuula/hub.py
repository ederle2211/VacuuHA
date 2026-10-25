from __future__ import annotations

from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_ROBOTS_PATH


class VacuulaHub:
    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        self.base_url = f"http://{host}:{port}"
        self._session = async_get_clientsession(hass)

    async def async_get_robots(self) -> dict[str, dict[str, Any]]:
        url = f"{self.base_url}{API_ROBOTS_PATH}"

        async with self._session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            response.raise_for_status()
            robots = await response.json(content_type=None)

        if not isinstance(robots, dict):
            raise ValueError("Vacuula returned an invalid robot list")

        if not all(isinstance(robot, dict) for robot in robots.values()):
            raise ValueError("Vacuula returned invalid robot data")

        return robots

    async def async_get_robot_state(self, serial: str) -> dict[str, Any]:
        url = f"{self.base_url}/api/robot/{serial}/command"

        async with self._session.post(
            url,
            json={"cmd": "getRobotState"},
            timeout=aiohttp.ClientTimeout(total=35),
        ) as response:
            response.raise_for_status()
            result = await response.json(content_type=None)

        if not isinstance(result, dict) or result.get("result") != "ok":
            raise ValueError(f"Invalid state response for robot {serial}")

        return result


    async def async_get_data(self) -> dict[str, dict[str, Any]]:
        robots = await self.async_get_robots()

        for serial, robot in robots.items():
            robot["status"] = None

            if robot.get("type") != "neato.gen3" or not robot.get("connected"):
                continue

            try:
                robot["status"] = await self.async_get_robot_state(serial)
            except (aiohttp.ClientError, TimeoutError, ValueError):
                robot["status"] = None

        return robots