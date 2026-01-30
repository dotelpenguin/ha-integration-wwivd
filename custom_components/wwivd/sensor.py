"""Sensor platform for WWIVD integration."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import aiohttp

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

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
    DEFAULT_PORT,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_MODEM_PORT,
    ENDPOINT_INSTANCES,
    ENDPOINT_BLOCKING,
    ENDPOINT_SYSOP,
    ENDPOINT_LASTON,
    ENDPOINT_MODEM_STATUS,
    SENSOR_USED_INSTANCES,
    SENSOR_AUTO_BLOCKED_COUNT,
    SENSOR_CALLS_TODAY,
    SENSOR_EMAIL_TODAY,
    SENSOR_FEEDBACK_TODAY,
    SENSOR_FEEDBACK_WAITING,
    SENSOR_LASTON_COUNT,
    SENSOR_LASTON,
    SENSOR_MODEM_STATUS,
    ATTR_LAST_UPDATED,
)

_LOGGER = logging.getLogger(__name__)


def _base_url(host: str, port: int) -> str:
    return f"http://{host}:{port}".rstrip("/")


def _get_int(data: dict[str, Any], *keys: str) -> int | None:
    """Return first key that exists and is int-like, else None."""
    for key in keys:
        if key in data:
            try:
                v = data[key]
                return int(v) if v is not None else None
            except (TypeError, ValueError):
                pass
    return None


def _get_list(data: dict[str, Any], *keys: str) -> list[Any]:
    """Return first key that exists and is a list, else []."""
    for key in keys:
        if key in data and isinstance(data[key], list):
            return data[key]
    return []


async def _fetch_json(session: aiohttp.ClientSession, url: str) -> dict[str, Any] | None:
    """GET URL and return JSON or None."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            return await resp.json()
    except (aiohttp.ClientError, ValueError):
        return None


class WWIVDCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches WWIVD endpoint data and exposes a flat dict of sensor values."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.config_entry = config_entry
        data = config_entry.data
        self._host = data[CONF_HOST].strip()
        self._port = data.get(CONF_PORT, DEFAULT_PORT)
        self._refresh = data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)
        self._enable_instances = data.get(CONF_ENABLE_INSTANCES, True)
        self._enable_blocking = data.get(CONF_ENABLE_BLOCKING, True)
        self._enable_sysop = data.get(CONF_ENABLE_SYSOP, True)
        self._enable_laston = data.get(CONF_ENABLE_LASTON, True)
        self._modem_enabled = data.get(CONF_MODEM_ENABLED, False)
        self._modem_host = (data.get(CONF_MODEM_HOST) or "").strip()
        self._modem_port = data.get(CONF_MODEM_PORT, DEFAULT_MODEM_PORT)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=self._refresh),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all enabled endpoints and return flat sensor dict."""
        result: dict[str, Any] = {
            ATTR_LAST_UPDATED: datetime.now(timezone.utc).isoformat(),
        }
        base = _base_url(self._host, self._port)

        async with aiohttp.ClientSession() as session:
            if self._enable_instances:
                raw = await _fetch_json(session, f"{base}{ENDPOINT_INSTANCES}")
                if raw is not None:
                    result[SENSOR_USED_INSTANCES] = _get_int(
                        raw, "used_instances", "used", "instances"
                    )
                if SENSOR_USED_INSTANCES not in result:
                    result[SENSOR_USED_INSTANCES] = None

            if self._enable_blocking:
                raw = await _fetch_json(session, f"{base}{ENDPOINT_BLOCKING}")
                if raw is not None:
                    result[SENSOR_AUTO_BLOCKED_COUNT] = _get_int(
                        raw, "auto_blocked_count", "auto_blocked", "blocked_count"
                    )
                if SENSOR_AUTO_BLOCKED_COUNT not in result:
                    result[SENSOR_AUTO_BLOCKED_COUNT] = None

            if self._enable_sysop:
                raw = await _fetch_json(session, f"{base}{ENDPOINT_SYSOP}")
                if raw is not None:
                    result[SENSOR_CALLS_TODAY] = _get_int(
                        raw, "calls_today", "calls"
                    )
                    result[SENSOR_EMAIL_TODAY] = _get_int(
                        raw, "email_today", "email"
                    )
                    result[SENSOR_FEEDBACK_TODAY] = _get_int(
                        raw, "feedback_today", "feedback"
                    )
                    result[SENSOR_FEEDBACK_WAITING] = _get_int(
                        raw, "feedback_waiting", "feedback_waiting"
                    )
                for key in (
                    SENSOR_CALLS_TODAY,
                    SENSOR_EMAIL_TODAY,
                    SENSOR_FEEDBACK_TODAY,
                    SENSOR_FEEDBACK_WAITING,
                ):
                    if key not in result:
                        result[key] = None

            if self._enable_laston:
                raw = await _fetch_json(session, f"{base}{ENDPOINT_LASTON}")
                if raw is not None:
                    lst = _get_list(raw, "laston", "users", "items", "data")
                    result[SENSOR_LASTON_COUNT] = len(lst) if lst is not None else 0
                    result[SENSOR_LASTON] = lst
                else:
                    result[SENSOR_LASTON_COUNT] = None
                    result[SENSOR_LASTON] = []

            if self._modem_enabled and self._modem_host:
                modem_base = _base_url(self._modem_host, self._modem_port)
                raw = await _fetch_json(
                    session, f"{modem_base}{ENDPOINT_MODEM_STATUS}"
                )
                if raw is not None:
                    result[SENSOR_MODEM_STATUS] = raw
                else:
                    result[SENSOR_MODEM_STATUS] = None
            else:
                result[SENSOR_MODEM_STATUS] = None

        return result


def _sensors_for_config(config_entry: ConfigEntry) -> list[tuple[str, str, str]]:
    """Return list of (sensor_key, name, icon) for enabled features."""
    data = config_entry.data
    out: list[tuple[str, str, str]] = []
    if data.get("enable_instances", True):
        out.append((SENSOR_USED_INSTANCES, "Used instances", "mdi:counter"))
    if data.get("enable_blocking", True):
        out.append((SENSOR_AUTO_BLOCKED_COUNT, "Auto blocked count", "mdi:block-helper"))
    if data.get("enable_sysop", True):
        out.append((SENSOR_CALLS_TODAY, "Calls today", "mdi:phone"))
        out.append((SENSOR_EMAIL_TODAY, "Email today", "mdi:email"))
        out.append((SENSOR_FEEDBACK_TODAY, "Feedback today", "mdi:message-text"))
        out.append((SENSOR_FEEDBACK_WAITING, "Feedback waiting", "mdi:message-alert"))
    if data.get("enable_laston", True):
        out.append((SENSOR_LASTON_COUNT, "Last on count", "mdi:account-group"))
    if data.get("modem_enabled", False) and data.get("modem_host"):
        out.append((SENSOR_MODEM_STATUS, "Modem status", "mdi:modem"))
    return out


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WWIVD sensors from a config entry."""
    coordinator = WWIVDCoordinator(hass, config_entry)
    hass.data[DOMAIN][config_entry.entry_id]["coordinator"] = coordinator

    entities = []
    for sensor_key, name, icon in _sensors_for_config(config_entry):
        entities.append(
            WWIVDSensor(coordinator, config_entry.entry_id, sensor_key, name, icon)
        )

    async_add_entities(entities)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.warning(
            "Initial WWIVD fetch failed: %s. Sensors may show unavailable until the server is reachable.",
            err,
        )


class WWIVDSensor(CoordinatorEntity[WWIVDCoordinator], SensorEntity):
    """Representation of a WWIVD sensor."""

    def __init__(
        self,
        coordinator: WWIVDCoordinator,
        entry_id: str,
        sensor_key: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._sensor_key = sensor_key
        self._attr_name = f"WWIVD {name}"
        self._attr_unique_id = f"{entry_id}_{sensor_key}"
        self._attr_icon = icon

    @property
    def native_value(self) -> int | str | None:
        """Return the state."""
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get(self._sensor_key)
        if val is None:
            return None
        if self._sensor_key == SENSOR_MODEM_STATUS:
            return "available" if isinstance(val, dict) and val else "unavailable"
        if isinstance(val, list):
            return len(val)
        if isinstance(val, dict):
            return len(val) if val else 0
        return val

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        if not self.coordinator.data:
            return {}
        attrs: dict[str, Any] = {
            ATTR_LAST_UPDATED: self.coordinator.data.get(ATTR_LAST_UPDATED),
        }
        if self._sensor_key == SENSOR_LASTON_COUNT:
            laston = self.coordinator.data.get(SENSOR_LASTON)
            if isinstance(laston, list) and laston:
                attrs["laston"] = laston[:20]
        if self._sensor_key == SENSOR_MODEM_STATUS:
            modem = self.coordinator.data.get(SENSOR_MODEM_STATUS)
            if isinstance(modem, dict):
                attrs["modem_status"] = modem
        return attrs
