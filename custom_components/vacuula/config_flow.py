from __future__ import annotations

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import (
    API_ROBOTS_PATH,
    CONF_HOST,
    CONF_PORT,
    DEFAULT_PORT,
    DOMAIN,
)


class VacuulaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _check_server(self, host: str, port: int) -> bool:
        """Return True if the Vacuula API responds with a robot list."""
        session = async_get_clientsession(self.hass)
        url = f"http://{host}:{port}{API_ROBOTS_PATH}"

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                response.raise_for_status()
                robots = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError):
            return False

        return isinstance(robots, dict)

    async def _create_entry(self, host: str, port: int) -> FlowResult:
        await self.async_set_unique_id(f"{host.lower()}:{port}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"Vacuula ({host}:{port})",
            data={
                CONF_HOST: host,
                CONF_PORT: port,
            },
        )

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]

            if await self._check_server(host, port):
                return await self._create_entry(host, port)

            errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1, max=65535),
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
    ) -> FlowResult:
        host = discovery_info.host
        port = discovery_info.port

        await self.async_set_unique_id(f"{host.lower()}:{port}")
        self._abort_if_unique_id_configured()

        if not await self._check_server(host, port):
            return self.async_abort(reason="cannot_connect")

        return self.async_create_entry(
            title=f"Vacuula ({host}:{port})",
            data={
                CONF_HOST: host,
                CONF_PORT: port,
            },
        )