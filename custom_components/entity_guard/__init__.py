"""Entity Guard integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENTRY_TYPE,
    DOMAIN,
    ENTRY_TYPE_HUB,
    ENTRY_TYPE_RULE,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS_HUB: list[Platform] = [Platform.SWITCH]
PLATFORMS_RULE: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Entity Guard from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    entry_type = entry.data.get(CONF_ENTRY_TYPE, ENTRY_TYPE_RULE)

    if entry_type == ENTRY_TYPE_HUB:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_HUB)
    else:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_RULE)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_type = entry.data.get(CONF_ENTRY_TYPE, ENTRY_TYPE_RULE)
    platforms = PLATFORMS_HUB if entry_type == ENTRY_TYPE_HUB else PLATFORMS_RULE

    return await hass.config_entries.async_unload_platforms(entry, platforms)
