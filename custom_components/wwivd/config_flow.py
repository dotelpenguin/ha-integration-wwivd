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
    _LOGGER.error("WWIVD OPTIONS: Building schema from data dict: %s", data)
    _LOGGER.error("WWIVD OPTIONS: Data dict type: %s", type(data))
    _LOGGER.error("WWIVD OPTIONS: Data dict keys: %s", list(data.keys()) if isinstance(data, dict) else "NOT A DICT")
    # Extract values with type safety - use CONF_* constants to read from data
    host = str(data.get(CONF_HOST, "") or "")
    port = int(data.get(CONF_PORT, DEFAULT_PORT) or DEFAULT_PORT)
    refresh = int(data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL) or DEFAULT_REFRESH_INTERVAL)
    enable_instances = bool(data.get(CONF_ENABLE_INSTANCES, True))
    enable_blocking = bool(data.get(CONF_ENABLE_BLOCKING, True))
    enable_sysop = bool(data.get(CONF_ENABLE_SYSOP, True))
    enable_laston = bool(data.get(CONF_ENABLE_LASTON, True))
    modem_enabled = bool(data.get(CONF_MODEM_ENABLED, False))
    modem_host = str(data.get(CONF_MODEM_HOST, "") or "")
    modem_port = int(data.get(CONF_MODEM_PORT, DEFAULT_MODEM_PORT) or DEFAULT_MODEM_PORT)
    modem_refresh = int(data.get(CONF_MODEM_REFRESH_INTERVAL, DEFAULT_MODEM_REFRESH_INTERVAL) or DEFAULT_MODEM_REFRESH_INTERVAL)
    _LOGGER.error("WWIVD OPTIONS: Schema defaults - host=%s, port=%s, refresh=%s, instances=%s, blocking=%s, sysop=%s, laston=%s", 
                   host, port, refresh, enable_instances, enable_blocking, enable_sysop, enable_laston)
    
    return vol.Schema(
        {
            vol.Required("host", default=host): str,
            vol.Required("port", default=port): int,
            vol.Required("refresh_interval", default=refresh): int,
            vol.Required("enable_instances", default=enable_instances): bool,
            vol.Required("enable_blocking", default=enable_blocking): bool,
            vol.Required("enable_sysop", default=enable_sysop): bool,
            vol.Required("enable_laston", default=enable_laston): bool,
            vol.Required("modem_enabled", default=modem_enabled): bool,
            vol.Optional("modem_host", default=modem_host): str,
            vol.Optional("modem_port", default=modem_port): int,
            vol.Optional("modem_refresh_interval", default=modem_refresh): int,
        }
    )


def _safe_options_data(config_entry: config_entries.ConfigEntry) -> dict[str, Any]:
    """Build a plain dict from config entry data and options; never raise.
    
    Note: config_entry.data/options are mappingproxy (immutable), not dict.
    Convert to dict using dict() constructor.
    """
    try:
        # Merge data and options (options override data for same keys)
        data = getattr(config_entry, "data", None)
        options = getattr(config_entry, "options", None)
        raw = {}
        # Handle mappingproxy (immutable dict-like) by converting to dict
        if data is not None:
            try:
                data_dict = dict(data)
                raw.update(data_dict)
                _LOGGER.error("WWIVD OPTIONS: Converted data mappingproxy to dict: %s", data_dict)
            except (TypeError, ValueError, AttributeError) as e:
                _LOGGER.error("WWIVD OPTIONS: Failed to convert data: %s", e)
        if options is not None:
            try:
                options_dict = dict(options)
                raw.update(options_dict)
                _LOGGER.error("WWIVD OPTIONS: Converted options mappingproxy to dict: %s", options_dict)
            except (TypeError, ValueError, AttributeError) as e:
                _LOGGER.error("WWIVD OPTIONS: Failed to convert options: %s", e)
        _LOGGER.error("WWIVD OPTIONS: _safe_options_data returning: %s", raw)
        return dict(raw)  # Return copy of all data
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.exception("Failed to load options data: %s", err)
        return {}


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle WWIVD options. config_entry is provided by parent OptionsFlow."""

    @property
    def _data(self) -> dict[str, Any]:
        """Load and cache config entry data (like jirafilters self._data pattern)."""
        if not hasattr(self, "_cached_data"):
            # Get fresh entry from config store to ensure we have latest data
            entry = self.hass.config_entries.async_get_entry(self.config_entry.entry_id)
            if entry:
                self._cached_data = _safe_options_data(entry)
            else:
                _LOGGER.warning("Config entry %s not found in store", self.config_entry.entry_id)
                self._cached_data = _safe_options_data(self.config_entry)
            _LOGGER.debug("Loaded config entry data: %s", self._cached_data)
        return self._cached_data

    def _options_form(
        self,
        data: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> FlowResult:
        """Show options form with optional error. data = current values for defaults."""
        if data is None:
            data = self._data
        _LOGGER.error("WWIVD OPTIONS: Building options form with data: %s", data)
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
                _LOGGER.error("WWIVD OPTIONS: Opening options form for entry_id=%s", self.config_entry.entry_id)
                # Direct access to see what's actually there
                _LOGGER.error("WWIVD OPTIONS: self.config_entry.data = %s", getattr(self.config_entry, "data", "NO DATA ATTR"))
                _LOGGER.error("WWIVD OPTIONS: self.config_entry.options = %s", getattr(self.config_entry, "options", "NO OPTIONS ATTR"))
                # Get fresh entry from config store to ensure we have latest saved data
                entry = self.hass.config_entries.async_get_entry(self.config_entry.entry_id)
                if entry:
                    _LOGGER.error("WWIVD OPTIONS: Found entry in store")
                    _LOGGER.error("WWIVD OPTIONS: entry.data = %s", getattr(entry, "data", "NO DATA"))
                    _LOGGER.error("WWIVD OPTIONS: entry.options = %s", getattr(entry, "options", "NO OPTIONS"))
                    current_data = _safe_options_data(entry)
                    _LOGGER.error("WWIVD OPTIONS: After _safe_options_data: %s", current_data)
                    return self._options_form(current_data)
                else:
                    _LOGGER.error("WWIVD OPTIONS: Entry not found in store, using self.config_entry")
                    fallback_data = _safe_options_data(self.config_entry)
                    _LOGGER.error("WWIVD OPTIONS: Fallback data: %s", fallback_data)
                    return self._options_form(fallback_data)
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

        # user_input uses string keys from schema, map to CONF_* constants for storage
        data_to_save = {
            CONF_HOST: user_input.get("host", ""),
            CONF_PORT: user_input.get("port", DEFAULT_PORT),
            CONF_REFRESH_INTERVAL: user_input.get("refresh_interval", DEFAULT_REFRESH_INTERVAL),
            CONF_ENABLE_INSTANCES: user_input.get("enable_instances", True),
            CONF_ENABLE_BLOCKING: user_input.get("enable_blocking", True),
            CONF_ENABLE_SYSOP: user_input.get("enable_sysop", True),
            CONF_ENABLE_LASTON: user_input.get("enable_laston", True),
            CONF_MODEM_ENABLED: user_input.get("modem_enabled", False),
        }
        if data_to_save.get(CONF_MODEM_ENABLED):
            data_to_save[CONF_MODEM_HOST] = user_input.get("modem_host", "")
            data_to_save[CONF_MODEM_PORT] = user_input.get("modem_port", DEFAULT_MODEM_PORT)
            data_to_save[CONF_MODEM_REFRESH_INTERVAL] = user_input.get("modem_refresh_interval", DEFAULT_MODEM_REFRESH_INTERVAL)

        self.hass.config_entries.async_update_entry(self.config_entry, data=data_to_save)
        # Clear cached data so next time we reload fresh
        if hasattr(self, "_cached_data"):
            delattr(self, "_cached_data")
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        return self.async_create_entry(title="", data={})
