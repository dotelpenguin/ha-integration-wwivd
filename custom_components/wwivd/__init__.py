"""The WWIVD integration."""
from __future__ import annotations

import logging

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _refresh_service_name(entry: ConfigEntry) -> str:
    """Build a safe refresh service name from the config entry."""
    connection_name = entry.data.get("name") or entry.title or "WWIVD"
    safe = "".join(
        c if c.isalnum() or c == " " else "_"
        for c in connection_name.lower().replace("-", " ")
    ).replace(" ", "_").strip("_") or "wwivd"
    return f"refresh_{safe}"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the WWIVD component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WWIVD from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": None, "modem_coordinator": None}

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    connection_name = entry.data.get("name") or entry.title or "WWIVD"
    service_name = _refresh_service_name(entry)

    async def handle_refresh(call: ServiceCall) -> None:
        entry_data = hass.data[DOMAIN][entry.entry_id]
        coordinator = entry_data.get("coordinator")
        modem_coordinator = entry_data.get("modem_coordinator")
        if coordinator:
            await coordinator.async_request_refresh()
        if modem_coordinator:
            await modem_coordinator.async_request_refresh()
        if coordinator or modem_coordinator:
            _LOGGER.info("Manually refreshed WWIVD data for %s", connection_name)
        else:
            _LOGGER.warning("No coordinator available for %s", connection_name)

    hass.services.async_register(DOMAIN, service_name, handle_refresh, schema=vol.Schema({}))
    _LOGGER.info("Registered service: %s.%s", DOMAIN, service_name)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        service_name = _refresh_service_name(entry)
        try:
            hass.services.async_remove(DOMAIN, service_name)
        except ValueError:
            pass
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
