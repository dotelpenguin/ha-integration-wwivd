"""Config flow for WWIVD integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_REFRESH_INTERVAL,
    CONF_ENABLE_INSTANCES,
    CONF_ENABLE_BLOCKING,
    CONF_ENABLE_SYSOP,
    CONF_ENABLE_LASTON,
    CONF_MODEM_ENABLED,
    CONF_MODEM_HOST,
    CONF_MODEM_PORT,
    CONF_MODEM_REFRESH_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_MODEM_PORT,
    DEFAULT_MODEM_REFRESH_INTERVAL,
    MIN_REFRESH_INTERVAL,
    ENDPOINT_INSTANCES,
    ENDPOINT_BLOCKING,
    ENDPOINT_SYSOP,
    ENDPOINT_LASTON,
    ENDPOINT_MODEM_STATUS,
)

_LOGGER = logging.getLogger(__name__)


def _base_url(host: str, port: int) -> str:
    """Build base URL (no trailing slash)."""
    return f"http://{host}:{port}".rstrip("/")


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=""): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_REFRESH_INTERVAL, default=DEFAULT_REFRESH_INTERVAL): int,
        vol.Required(CONF_ENABLE_INSTANCES, default=True): bool,
        vol.Required(CONF_ENABLE_BLOCKING, default=True): bool,
        vol.Required(CONF_ENABLE_SYSOP, default=True): bool,
        vol.Required(CONF_ENABLE_LASTON, default=True): bool,
        vol.Required(CONF_MODEM_ENABLED, default=False): bool,
    }
)

STEP_MODEM_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MODEM_HOST, default=""): str,
        vol.Required(CONF_MODEM_PORT, default=DEFAULT_MODEM_PORT): int,
        vol.Required(
            CONF_MODEM_REFRESH_INTERVAL,
            default=DEFAULT_MODEM_REFRESH_INTERVAL,
        ): int,
    }
)


async def _fetch_json(hass: HomeAssistant, url: str) -> dict[str, Any] | None:
    """GET URL and return JSON or None on failure."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
    except (aiohttp.ClientError, ValueError) as e:
        _LOGGER.debug("Fetch %s failed: %s", url, e)
        return None


async def validate_wwivd(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate that we can reach enabled WWIVD endpoints."""
    host = data[CONF_HOST].strip()
    port = data[CONF_PORT]
    base = _base_url(host, port)

    endpoints_to_check = []
    if data.get(CONF_ENABLE_INSTANCES, True):
        endpoints_to_check.append((ENDPOINT_INSTANCES, f"{base}{ENDPOINT_INSTANCES}"))
    if data.get(CONF_ENABLE_BLOCKING, True):
        endpoints_to_check.append((ENDPOINT_BLOCKING, f"{base}{ENDPOINT_BLOCKING}"))
    if data.get(CONF_ENABLE_SYSOP, True):
        endpoints_to_check.append((ENDPOINT_SYSOP, f"{base}{ENDPOINT_SYSOP}"))
    if data.get(CONF_ENABLE_LASTON, True):
        endpoints_to_check.append((ENDPOINT_LASTON, f"{base}{ENDPOINT_LASTON}"))

    if not endpoints_to_check:
        raise InvalidConfig("At least one endpoint must be enabled.")

    for path, url in endpoints_to_check:
        result = await _fetch_json(hass, url)
        if result is None:
            raise CannotConnect(f"Failed to reach {path}")


async def validate_modem(hass: HomeAssistant, host: str, port: int) -> None:
    """Validate Modem Manager endpoint."""
    base = _base_url(host, port)
    url = f"{base}{ENDPOINT_MODEM_STATUS}"
    result = await _fetch_json(hass, url)
    if result is None:
        raise CannotConnect(f"Failed to reach Modem Manager at {url}")


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidConfig(HomeAssistantError):
    """Error to indicate invalid configuration."""


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WWIVD."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                description_placeholders={
                    "docs": "https://github.com/dotelpenguin/ha-integration-wwivd",
                },
            )

        errors: dict[str, str] = {}

        if user_input.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL) < MIN_REFRESH_INTERVAL:
            errors["base"] = "invalid_refresh_interval"

        if not errors:
            try:
                await validate_wwivd(self.hass, user_input)
            except InvalidConfig as e:
                errors["base"] = "invalid_config"
                _LOGGER.warning("Invalid config: %s", e)
            except CannotConnect as e:
                errors["base"] = "cannot_connect"
                _LOGGER.warning("Cannot connect: %s", e)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error validating WWIVD")
                errors["base"] = "unknown"

        if errors:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors=errors,
            )

        self._data = dict(user_input)

        if user_input.get(CONF_MODEM_ENABLED):
            return await self.async_step_modem()

        return self._create_entry()

    async def async_step_modem(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle Modem Manager step."""
        if user_input is None:
            return self.async_show_form(
                step_id="modem",
                data_schema=STEP_MODEM_DATA_SCHEMA,
            )

        errors: dict[str, str] = {}
        if user_input.get(CONF_MODEM_REFRESH_INTERVAL, DEFAULT_MODEM_REFRESH_INTERVAL) < MIN_REFRESH_INTERVAL:
            errors["base"] = "invalid_refresh_interval"
        if not errors:
            try:
                await validate_modem(
                    self.hass,
                    user_input[CONF_MODEM_HOST].strip(),
                    user_input[CONF_MODEM_PORT],
                )
            except CannotConnect:
                errors["base"] = "cannot_connect_modem"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error validating Modem Manager")
                errors["base"] = "unknown"

        if errors:
            return self.async_show_form(
                step_id="modem",
                data_schema=STEP_MODEM_DATA_SCHEMA,
                errors=errors,
            )

        self._data[CONF_MODEM_HOST] = user_input[CONF_MODEM_HOST].strip()
        self._data[CONF_MODEM_PORT] = user_input[CONF_MODEM_PORT]
        self._data[CONF_MODEM_REFRESH_INTERVAL] = user_input[CONF_MODEM_REFRESH_INTERVAL]
        return self._create_entry()

    def _create_entry(self) -> FlowResult:
        """Create config entry from collected data."""
        host = self._data[CONF_HOST].strip()
        port = self._data[CONF_PORT]
        title = f"WWIVD - {host}:{port}"
        return self.async_create_entry(title=title, data=self._data)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow. Handler gets config_entry from parent."""
        return OptionsFlowHandler()


def _options_schema(data: dict[str, Any] | None) -> vol.Schema:
    """Build options form schema from current data. Coerce None to safe defaults."""
    if data is None:
        data = {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=(data.get(CONF_HOST) or "")): str,
            vol.Required(
                CONF_PORT,
                default=DEFAULT_PORT if data.get(CONF_PORT) is None else data.get(CONF_PORT),
            ): int,
            vol.Required(
                CONF_REFRESH_INTERVAL,
                default=(
                    DEFAULT_REFRESH_INTERVAL
                    if data.get(CONF_REFRESH_INTERVAL) is None
                    else data.get(CONF_REFRESH_INTERVAL)
                ),
            ): int,
            vol.Required(
                CONF_ENABLE_INSTANCES,
                default=data.get(CONF_ENABLE_INSTANCES, True) is not False,
            ): bool,
            vol.Required(
                CONF_ENABLE_BLOCKING,
                default=data.get(CONF_ENABLE_BLOCKING, True) is not False,
            ): bool,
            vol.Required(
                CONF_ENABLE_SYSOP,
                default=data.get(CONF_ENABLE_SYSOP, True) is not False,
            ): bool,
            vol.Required(
                CONF_ENABLE_LASTON,
                default=data.get(CONF_ENABLE_LASTON, True) is not False,
            ): bool,
            vol.Required(
                CONF_MODEM_ENABLED,
                default=data.get(CONF_MODEM_ENABLED, False) is True,
            ): bool,
            vol.Optional(
                CONF_MODEM_HOST,
                default=(data.get(CONF_MODEM_HOST) or ""),
            ): str,
            vol.Optional(
                CONF_MODEM_PORT,
                default=(
                    DEFAULT_MODEM_PORT
                    if data.get(CONF_MODEM_PORT) is None
                    else data.get(CONF_MODEM_PORT)
                ),
            ): int,
            vol.Optional(
                CONF_MODEM_REFRESH_INTERVAL,
                default=(
                    DEFAULT_MODEM_REFRESH_INTERVAL
                    if data.get(CONF_MODEM_REFRESH_INTERVAL) is None
                    else data.get(CONF_MODEM_REFRESH_INTERVAL)
                ),
            ): int,
        }
    )


def _safe_options_data(config_entry: config_entries.ConfigEntry) -> dict[str, Any]:
    """Build a plain dict from config entry data and options; never raise."""
    result: dict[str, Any] = {}
    try:
        # Merge data and options (options override data for same keys)
        data = getattr(config_entry, "data", None)
        options = getattr(config_entry, "options", None)
        raw = {}
        if isinstance(data, dict):
            raw.update(data)
        if isinstance(options, dict):
            raw.update(options)
        if not raw:
            _LOGGER.debug("Config entry has no data or options")
            return {}
        # Filter to known config keys
        known_keys = (
            CONF_HOST, CONF_PORT, CONF_REFRESH_INTERVAL,
            CONF_ENABLE_INSTANCES, CONF_ENABLE_BLOCKING,
            CONF_ENABLE_SYSOP, CONF_ENABLE_LASTON,
            CONF_MODEM_ENABLED, CONF_MODEM_HOST, CONF_MODEM_PORT,
            CONF_MODEM_REFRESH_INTERVAL,
        )
        result = {k: v for k, v in raw.items() if k in known_keys}
        _LOGGER.debug("Loaded options data: %s (from keys: %s)", result, list(raw.keys()))
        return result
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.exception("Failed to load options data: %s", err)
        return {}


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle WWIVD options. config_entry is provided by parent OptionsFlow."""

    def _options_form(
        self,
        data: dict[str, Any],
        error: str | None = None,
    ) -> FlowResult:
        """Show options form with optional error. data = current values for defaults."""
        errors = {"base": error} if error else {}
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(data),
            errors=errors,
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is None:
            try:
                # self.config_entry is provided by parent OptionsFlow
                current = _safe_options_data(self.config_entry)
                _LOGGER.debug("Options form data: %s", current)
                return self._options_form(current)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Options flow failed to show form: %s", err)
                return self.async_abort(reason="options_load_failed")

        refresh = user_input.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)
        any_endpoint = (
            user_input.get(CONF_ENABLE_INSTANCES, True)
            or user_input.get(CONF_ENABLE_BLOCKING, True)
            or user_input.get(CONF_ENABLE_SYSOP, True)
            or user_input.get(CONF_ENABLE_LASTON, True)
        )
        if refresh < MIN_REFRESH_INTERVAL:
            return self._options_form(user_input, "invalid_refresh_interval")
        if not any_endpoint:
            return self._options_form(user_input, "invalid_config")
        if user_input.get(CONF_MODEM_ENABLED) and user_input.get(
            CONF_MODEM_REFRESH_INTERVAL, DEFAULT_MODEM_REFRESH_INTERVAL
        ) < MIN_REFRESH_INTERVAL:
            return self._options_form(user_input, "invalid_refresh_interval")

        data_to_save = dict(user_input)
        if not data_to_save.get(CONF_MODEM_ENABLED):
            data_to_save.pop(CONF_MODEM_HOST, None)
            data_to_save.pop(CONF_MODEM_PORT, None)
            data_to_save.pop(CONF_MODEM_REFRESH_INTERVAL, None)

        self.hass.config_entries.async_update_entry(self.config_entry, data=data_to_save)
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        return self.async_create_entry(title="", data={})
