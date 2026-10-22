from __future__ import annotations

import aiohttp
import voluptuous as vol

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import API_ROBOTS_PATH, CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN


class VacuulaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovered_host: str | None = None
        self._discovered_port: int | None = None
        self._discovered_robot_count: int = 0

    async def _async_get_robots(
        self, host: str, port: int
    ) -> dict[str, dict[str, Any]] | None:
        """Return the registered robots, or None if the server response is invalid."""
        url = f"http://{host}:{port}{API_ROBOTS_PATH}"

        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                response.raise_for_status()
                robots = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, ValueError):
            return None

        if not isinstance(robots, dict):
            return None
        if not all(isinstance(robot, dict) for robot in robots.values()):
            return None

        return robots

    async def _async_create_entry(self, host: str, port: int) -> ConfigFlowResult:
        await self.async_set_unique_id(f"{host.lower()}:{port}")

        return self.async_create_entry(
            title=f"Vacuula ({host}:{port})",
            data={
                CONF_HOST: host,
                CONF_PORT: port,
            },
        )

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Handle user initiated flow. """
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]

            if await self._async_get_robots(host, port) is not None:
                await self.async_set_unique_id(f"{host.lower()}:{port}")
                self._abort_if_unique_id_configured()
                return await self._async_create_entry(host, port)

            errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle a Zeroconf discovery flow."""
        host = discovery_info.host
        port = discovery_info.port

        if port is None:
            return self.async_abort(reason="invalid_discovery_info")

        robots = await self._async_get_robots(host, port)
        if robots is None:
            return self.async_abort(reason="cannot_connect")
        
        await self.async_set_unique_id(f"{host.lower()}:{port}")

        self._abort_if_unique_id_configured(
            updates={
                CONF_HOST: host,
                CONF_PORT: port,
            }
        )

        self._discovered_host = host
        self._discovered_port = port
        self._discovered_robot_count = len(robots)

        self.context["title_placeholders"] = {
            "host": host,
            "port": str(port),
            "robot_count": str(self._discovered_robot_count),
        }

        # CHANGED: Confirm-only hier setzen, nicht im Confirm-Step.
        self._set_confirm_only()

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "host": host,
                "port": str(port),
                "robot_count": str(self._discovered_robot_count),
            },
        )

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle confirmation of a discovered server."""
        host = self._discovered_host
        port = self._discovered_port

        if host is None or port is None:
            return self.async_abort(reason="invalid_discovery_info")

        if user_input is None:
            return self._show_zeroconf_confirm_form(host, port)
        robots = await self._async_get_robots(host, port)
        if robots is None:
            return self._show_zeroconf_confirm_form(
                host, port, errors={"base": "cannot_connect"}
            )
        return await self._async_create_entry(host, port)

    def _show_zeroconf_confirm_form(
        self,
        host: str,
        port: int,
        *,
        errors: dict[str, str] | None = None,
    ) -> ConfigFlowResult:
        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema({}),
            errors=errors or {},
            description_placeholders={"host": host, "port": str(port), "robot_count": str(self._discovered_robot_count),},
        )