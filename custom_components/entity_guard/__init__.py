"""Entity Guard integration."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENTRY_TYPE,
    DOMAIN,
    ENTRY_TYPE_HUB,
    ENTRY_TYPE_RULE,
)
from .models import parse_rule_config
from .rule_engine import RuleEngine, signal_for_rule, signal_master_update
from .services import async_register_services
from .storage import EntityGuardStore

__all__ = ["signal_for_rule", "signal_master_update"]

_LOGGER = logging.getLogger(__name__)

PLATFORMS_HUB: list[Platform] = [Platform.SWITCH]
PLATFORMS_RULE: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

CARD_FILENAME = "entity-guard-card.js"
CARD_URL = f"/entity_guard/{CARD_FILENAME}"
_CARD_INSTALLED_KEY = "_card_installed"


def _get_version() -> str:
    """Get integration version from manifest."""
    manifest = Path(__file__).parent / "manifest.json"
    with manifest.open() as f:
        return json.load(f).get("version", "0.0.0")


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Entity Guard integration."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("engines", {})
    hass.data[DOMAIN].setdefault("hub_master_enabled", True)
    hass.data[DOMAIN].setdefault("hub", None)
    if "storage" not in hass.data[DOMAIN]:
        store = EntityGuardStore(hass)
        await store.async_load()
        hass.data[DOMAIN]["storage"] = store
    await async_register_services(hass)
    return True


def _master_enabled_getter(hass: HomeAssistant):
    """Return a callable resolving the current master switch state."""

    def _get() -> bool:
        domain_data = hass.data.get(DOMAIN, {})
        hub = domain_data.get("hub")
        if hub is not None:
            return bool(getattr(hub, "enabled", True))
        return bool(domain_data.get("hub_master_enabled", True))

    return _get


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Entity Guard from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("engines", {})
    hass.data[DOMAIN].setdefault("hub_master_enabled", True)
    hass.data[DOMAIN].setdefault("hub", None)
    if "storage" not in hass.data[DOMAIN]:
        store = EntityGuardStore(hass)
        await store.async_load()
        hass.data[DOMAIN]["storage"] = store

    entry_type = entry.data.get(CONF_ENTRY_TYPE, ENTRY_TYPE_RULE)

    if entry_type == ENTRY_TYPE_HUB:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_HUB)
    else:
        config = parse_rule_config(entry)
        store = hass.data[DOMAIN]["storage"]
        engine = RuleEngine(hass, config, store, _master_enabled_getter(hass))
        await engine.async_setup()
        hass.data[DOMAIN]["engines"][entry.entry_id] = engine
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_RULE)

    await _async_install_card(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_type = entry.data.get(CONF_ENTRY_TYPE, ENTRY_TYPE_RULE)
    platforms = PLATFORMS_HUB if entry_type == ENTRY_TYPE_HUB else PLATFORMS_RULE

    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)

    if unload_ok and entry_type == ENTRY_TYPE_RULE:
        engines = hass.data.get(DOMAIN, {}).get("engines", {})
        engine = engines.pop(entry.entry_id, None)
        if engine is not None:
            await engine.async_unload()

    return unload_ok


async def _async_install_card(hass: HomeAssistant) -> None:
    """Serve card JS from component dir and register as Lovelace resource."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_CARD_INSTALLED_KEY):
        return

    source = Path(__file__).parent / "frontend" / CARD_FILENAME
    if not source.exists():
        _LOGGER.warning("Card JS not found at %s", source)
        return

    version = await hass.async_add_executor_job(_get_version)

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(source), True)]
        )
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Static path %s already registered", CARD_URL)

    try:
        add_extra_js_url(hass, f"{CARD_URL}?{version}")
    except Exception:  # noqa: BLE001
        _LOGGER.debug("extra_js_url already registered for %s", CARD_URL)

    await _async_register_lovelace_resource(hass, version)
    hass.data[DOMAIN][_CARD_INSTALLED_KEY] = True


async def _async_register_lovelace_resource(hass: HomeAssistant, version: str) -> None:
    """Register card as Lovelace resource (best-effort)."""
    resource_url = f"{CARD_URL}?automatically-added&{version}"

    try:
        resources = hass.data["lovelace"].resources
    except (KeyError, AttributeError):
        _LOGGER.info(
            "Could not auto-register Lovelace resource. "
            "Add manually: url: %s, type: module",
            resource_url,
        )
        return

    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True

    existing = [r for r in resources.async_items() if CARD_FILENAME in r.get("url", "")]

    if not existing:
        if getattr(resources, "async_create_item", None):
            await resources.async_create_item(
                {"res_type": "module", "url": resource_url}
            )
            _LOGGER.info("Registered %s as Lovelace resource", resource_url)
        elif getattr(resources, "data", None) and getattr(
            resources.data, "append", None
        ):
            resources.data.append({"type": "module", "url": resource_url})
        return

    for r in existing[1:]:
        if isinstance(resources, ResourceStorageCollection):
            await resources.async_delete_item(r["id"])

    first = existing[0]
    if first.get("url") != resource_url and isinstance(
        resources, ResourceStorageCollection
    ):
        await resources.async_update_item(
            first["id"], {"res_type": "module", "url": resource_url}
        )
