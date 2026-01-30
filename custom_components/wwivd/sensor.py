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
    CONF_MODEM_REFRESH_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_MODEM_PORT,
    DEFAULT_MODEM_REFRESH_INTERVAL,
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
    DATA_INSTANCES,
    DATA_BLOCKING,
    DATA_SYSOP,
    DATA_LASTON,
    ATTR_LAST_UPDATED,
    ATTR_JSON_PAYLOAD,
)

# Map sensor_key -> coordinator data key for raw JSON payload
SENSOR_TO_PAYLOAD_KEY: dict[str, str] = {
    SENSOR_USED_INSTANCES: DATA_INSTANCES,
    SENSOR_AUTO_BLOCKED_COUNT: DATA_BLOCKING,
    SENSOR_CALLS_TODAY: DATA_SYSOP,
    SENSOR_EMAIL_TODAY: DATA_SYSOP,
    SENSOR_FEEDBACK_TODAY: DATA_SYSOP,
    SENSOR_FEEDBACK_WAITING: DATA_SYSOP,
    SENSOR_LASTON_COUNT: DATA_LASTON,
}

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


def _find_int_in_value(val: Any, keys: tuple[str, ...], depth: int, max_depth: int) -> int | None:
    """Recursively find first int value for any of the given keys (depth-limited)."""
    if depth > max_depth or val is None:
        return None
    if isinstance(val, dict):
        v = _get_int(val, *keys)
        if v is not None:
            return v
        for k, child in val.items():
            v = _find_int_in_value(child, keys, depth + 1, max_depth)
            if v is not None:
                return v
        return None
    if isinstance(val, list):
        for item in val:
            v = _find_int_in_value(item, keys, depth + 1, max_depth)
            if v is not None:
                return v
        return None
    return None


def _get_int_from_payload(payload: Any, *keys: str) -> int | None:
    """Get int from JSON payload: try known paths first, then search recursively."""
    if payload is None:
        return None
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        payload = payload[0]
    if not isinstance(payload, dict):
        return None
    v = _get_int(payload, *keys)
    if v is not None:
        return v
    for nest in ("status", "data", "instances", "result"):
        if nest in payload and isinstance(payload[nest], dict):
            v = _get_int(payload[nest], *keys)
            if v is not None:
                return v
    return _find_int_in_value(payload, keys, 0, max_depth=6)


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
    """Fetches WWIVD endpoint data (instances, blocking, sysop, laston) on its own schedule."""

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

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=self._refresh),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch enabled WWIVD endpoints (no Modem Manager)."""
        result: dict[str, Any] = {
            ATTR_LAST_UPDATED: datetime.now(timezone.utc).isoformat(),
        }
        base = _base_url(self._host, self._port)

        async with aiohttp.ClientSession() as session:
            if self._enable_instances:
                raw = await _fetch_json(session, f"{base}{ENDPOINT_INSTANCES}")
                result[DATA_INSTANCES] = raw
                if raw is not None:
                    result[SENSOR_USED_INSTANCES] = _get_int_from_payload(
                        raw, "used_instances", "usedInstances", "used", "instances"
                    )
                if SENSOR_USED_INSTANCES not in result:
                    result[SENSOR_USED_INSTANCES] = None

            if self._enable_blocking:
                raw = await _fetch_json(session, f"{base}{ENDPOINT_BLOCKING}")
                result[DATA_BLOCKING] = raw
                if raw is not None:
                    result[SENSOR_AUTO_BLOCKED_COUNT] = _get_int(
                        raw, "auto_blocked_count", "auto_blocked", "blocked_count"
                    )
                if SENSOR_AUTO_BLOCKED_COUNT not in result:
                    result[SENSOR_AUTO_BLOCKED_COUNT] = None

            if self._enable_sysop:
                raw = await _fetch_json(session, f"{base}{ENDPOINT_SYSOP}")
                result[DATA_SYSOP] = raw
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
                result[DATA_LASTON] = raw
                if raw is not None:
                    lst = _get_list(raw, "laston", "users", "items", "data")
                    result[SENSOR_LASTON_COUNT] = len(lst) if lst is not None else 0
                    result[SENSOR_LASTON] = lst
                else:
                    result[SENSOR_LASTON_COUNT] = None
                    result[SENSOR_LASTON] = []

        return result


class ModemCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches Modem Manager /modem_status on its own host, port, and refresh interval."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.config_entry = config_entry
        data = config_entry.data
        self._host = (data.get(CONF_MODEM_HOST) or "").strip()
        self._port = data.get(CONF_MODEM_PORT, DEFAULT_MODEM_PORT)
        self._refresh = data.get(
            CONF_MODEM_REFRESH_INTERVAL, DEFAULT_MODEM_REFRESH_INTERVAL
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_modem",
            update_interval=timedelta(seconds=self._refresh),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch Modem Manager endpoint only."""
        result: dict[str, Any] = {
            ATTR_LAST_UPDATED: datetime.now(timezone.utc).isoformat(),
            SENSOR_MODEM_STATUS: None,
        }
        if not self._host:
            return result
        base = _base_url(self._host, self._port)
        url = f"{base}{ENDPOINT_MODEM_STATUS}"
        async with aiohttp.ClientSession() as session:
            raw = await _fetch_json(session, url)
            if raw is not None:
                result[SENSOR_MODEM_STATUS] = raw
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
    entry_id = config_entry.entry_id
    coordinator = WWIVDCoordinator(hass, config_entry)
    hass.data[DOMAIN][entry_id]["coordinator"] = coordinator

    modem_coordinator = None
    if config_entry.data.get(CONF_MODEM_ENABLED) and config_entry.data.get(
        CONF_MODEM_HOST
    ):
        modem_coordinator = ModemCoordinator(hass, config_entry)
        hass.data[DOMAIN][entry_id]["modem_coordinator"] = modem_coordinator

    entities = []
    for sensor_key, name, icon in _sensors_for_config(config_entry):
        if sensor_key == SENSOR_MODEM_STATUS and modem_coordinator is not None:
            entities.append(
                WWIVDSensor(
                    modem_coordinator, entry_id, sensor_key, name, icon
                )
            )
        elif sensor_key != SENSOR_MODEM_STATUS:
            entities.append(
                WWIVDSensor(coordinator, entry_id, sensor_key, name, icon)
            )

    async_add_entities(entities)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.warning(
            "Initial WWIVD fetch failed: %s. Sensors may show unavailable until the server is reachable.",
            err,
        )
    if modem_coordinator is not None:
        try:
            await modem_coordinator.async_config_entry_first_refresh()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning(
                "Initial Modem Manager fetch failed: %s. Modem sensor may show unavailable.",
                err,
            )


class WWIVDSensor(
    CoordinatorEntity[DataUpdateCoordinator[dict[str, Any]]], SensorEntity
):
    """Representation of a WWIVD sensor (WWIVD or Modem coordinator)."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
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
        """Return extra attributes including raw JSON payload for the endpoint."""
        if not self.coordinator.data:
            return {}
        attrs: dict[str, Any] = {
            ATTR_LAST_UPDATED: self.coordinator.data.get(ATTR_LAST_UPDATED),
        }
        if self._sensor_key == SENSOR_MODEM_STATUS:
            payload = self.coordinator.data.get(SENSOR_MODEM_STATUS)
            if isinstance(payload, dict):
                attrs[ATTR_JSON_PAYLOAD] = payload
        else:
            payload_key = SENSOR_TO_PAYLOAD_KEY.get(self._sensor_key)
            if payload_key:
                payload = self.coordinator.data.get(payload_key)
                if payload is not None:
                    attrs[ATTR_JSON_PAYLOAD] = payload
        if self._sensor_key == SENSOR_LASTON_COUNT:
            laston = self.coordinator.data.get(SENSOR_LASTON)
            if isinstance(laston, list) and laston:
                attrs["laston"] = laston[:20]
        return attrs
