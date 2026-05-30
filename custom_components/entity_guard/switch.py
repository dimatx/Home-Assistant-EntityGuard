"""Switch platform for Entity Guard."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DEBOUNCE_ENABLED,
    CONF_ENTRY_TYPE,
    DEFAULT_DEBOUNCE_ENABLED,
    DOMAIN,
    ENTRY_TYPE_HUB,
    ENTRY_TYPE_RULE,
)

if TYPE_CHECKING:
    from .rule_engine import RuleEngine

_LOGGER = logging.getLogger(__name__)


def _signal_for_rule(rule_id: str) -> str:
    """Return dispatcher signal name for a rule."""
    try:
        from . import signal_for_rule  # type: ignore[attr-defined]

        return signal_for_rule(rule_id)
    except (ImportError, AttributeError):
        return f"entity_guard_rule_update_{rule_id}"


def _signal_master() -> str:
    """Return dispatcher signal name for master updates."""
    try:
        from . import signal_master_update  # type: ignore[attr-defined]

        return signal_master_update
    except (ImportError, AttributeError):
        return "entity_guard_master_update"


def _rule_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return device info for a rule entry."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Entity Guard",
        model="Rule",
    )


def _hub_device_info() -> DeviceInfo:
    """Return device info for the hub entry."""
    return DeviceInfo(
        identifiers={(DOMAIN, "hub")},
        name="Entity Guard Hub",
        manufacturer="Entity Guard",
        model="Hub",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Entity Guard switches from a config entry."""
    entry_type = entry.data.get(CONF_ENTRY_TYPE)

    if entry_type == ENTRY_TYPE_HUB:
        async_add_entities([EntityGuardMasterEnabledSwitch(hass, entry)])
        return

    if entry_type != ENTRY_TYPE_RULE:
        return

    engine: RuleEngine = hass.data[DOMAIN]["engines"][entry.entry_id]
    async_add_entities(
        [
            EntityGuardEnabledSwitch(entry, engine),
            EntityGuardDebounceEnabledSwitch(entry, engine),
        ]
    )


class EntityGuardRuleSwitchBase(SwitchEntity):
    """Base class for per-rule switches."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        entry: ConfigEntry,
        engine: RuleEngine,
        translation_key: str,
        suffix: str,
    ) -> None:
        """Initialize the switch."""
        self._entry = entry
        self._engine = engine
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_device_info = _rule_device_info(entry)

    async def async_added_to_hass(self) -> None:
        """Subscribe to dispatcher updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                _signal_for_rule(self._entry.entry_id),
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, *args: object) -> None:
        """Handle a dispatcher update."""
        self.async_write_ha_state()


class EntityGuardEnabledSwitch(EntityGuardRuleSwitchBase):
    """Switch toggling whether the rule is enabled."""

    def __init__(self, entry: ConfigEntry, engine: RuleEngine) -> None:
        """Initialize the enabled switch."""
        super().__init__(entry, engine, "enabled", "enabled")

    @property
    def is_on(self) -> bool:
        """Return True if the rule is enabled."""
        return bool(getattr(self._engine, "enabled", True))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the rule."""
        await self._set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the rule."""
        await self._set_enabled(False)

    async def _set_enabled(self, value: bool) -> None:
        """Apply enabled state through the engine."""
        setter = getattr(self._engine, "async_set_enabled", None)
        if setter is not None:
            await setter(value)
        else:
            self._engine.enabled = value  # type: ignore[attr-defined]
            async_dispatcher_send(self.hass, _signal_for_rule(self._entry.entry_id))
        self.async_write_ha_state()


class EntityGuardDebounceEnabledSwitch(EntityGuardRuleSwitchBase):
    """Switch toggling debounce behaviour."""

    def __init__(self, entry: ConfigEntry, engine: RuleEngine) -> None:
        """Initialize the debounce switch."""
        super().__init__(entry, engine, "debounce_enabled", "debounce_enabled")

    @property
    def is_on(self) -> bool:
        """Return True if debounce is enabled."""
        config = getattr(self._engine, "config", None)
        return bool(getattr(config, "debounce_enabled", DEFAULT_DEBOUNCE_ENABLED))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable debounce."""
        await self._set_debounce(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable debounce."""
        await self._set_debounce(False)

    async def _set_debounce(self, value: bool) -> None:
        """Persist debounce_enabled to engine config and config entry."""
        config = getattr(self._engine, "config", None)
        if config is not None:
            try:
                setattr(config, "debounce_enabled", value)
            except Exception:  # pragma: no cover - defensive
                _LOGGER.debug("Failed to update engine config debounce_enabled")

        new_data = dict(self._entry.data)
        new_data[CONF_DEBOUNCE_ENABLED] = value
        self.hass.config_entries.async_update_entry(self._entry, data=new_data)

        async_dispatcher_send(self.hass, _signal_for_rule(self._entry.entry_id))
        self.async_write_ha_state()


class EntityGuardMasterEnabledSwitch(SwitchEntity):
    """Hub-wide master enable switch."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "master_enabled"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the master switch."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_master_enabled"
        self._attr_device_info = _hub_device_info()
        hass.data.setdefault(DOMAIN, {}).setdefault("hub_master_enabled", True)

    @property
    def is_on(self) -> bool:
        """Return True if master enable is on."""
        return bool(self.hass.data.get(DOMAIN, {}).get("hub_master_enabled", True))

    async def async_added_to_hass(self) -> None:
        """Subscribe to master dispatcher updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, _signal_master(), self._handle_update)
        )

    @callback
    def _handle_update(self, *args: object) -> None:
        """Handle dispatcher update."""
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable master switch."""
        await self._set_master(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable master switch."""
        await self._set_master(False)

    async def _set_master(self, value: bool) -> None:
        """Apply the master switch state."""
        self.hass.data.setdefault(DOMAIN, {})["hub_master_enabled"] = value
        async_dispatcher_send(self.hass, _signal_master())
        self.async_write_ha_state()
