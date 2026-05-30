"""Services for Entity Guard."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_RULE_ID,
    DOMAIN,
    SERVICE_CLEAR_HISTORY,
    SERVICE_LIST_RULES,
    SERVICE_PANIC_STOP,
    SERVICE_SUPPRESS,
    SERVICE_UNSUPPRESS,
)

_LOGGER = logging.getLogger(__name__)

CONF_DURATION_MINUTES = "duration_minutes"

PANIC_STOP_DURATION_MINUTES = 60

SIGNAL_MASTER_UPDATED = f"{DOMAIN}_master_updated"

SUPPRESS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_RULE_ID): cv.string,
        vol.Required(CONF_DURATION_MINUTES): vol.All(
            cv.positive_int, vol.Range(min=1, max=1440)
        ),
    }
)

UNSUPPRESS_SCHEMA = vol.Schema({vol.Required(CONF_RULE_ID): cv.string})

CLEAR_HISTORY_SCHEMA = vol.Schema({vol.Required(CONF_RULE_ID): cv.string})

LIST_RULES_SCHEMA = vol.Schema({})

PANIC_STOP_SCHEMA = vol.Schema({})


def _iter_engines(hass: HomeAssistant) -> list[Any]:
    """Return all rule engines."""
    return list(hass.data.get(DOMAIN, {}).get("engines", {}).values())


def _resolve_engine(hass: HomeAssistant, rule_id: str) -> Any:
    """Resolve an engine by unique_id or rule name."""
    for engine in _iter_engines(hass):
        config = engine.config
        if config.unique_id == rule_id or config.name == rule_id:
            return engine
    raise ServiceValidationError(
        f"No Entity Guard rule found matching '{rule_id}'"
    )


async def async_register_services(hass: HomeAssistant) -> None:
    """Register Entity Guard services."""

    async def handle_suppress(call: ServiceCall) -> None:
        rule_id: str = call.data[CONF_RULE_ID]
        duration_minutes: int = call.data[CONF_DURATION_MINUTES]
        engine = _resolve_engine(hass, rule_id)
        await engine.async_suppress(
            duration_minutes=duration_minutes,
            user_id=call.context.user_id,
        )
        _LOGGER.info(
            "Suppressed rule %s for %d minute(s)",
            engine.config.name,
            duration_minutes,
        )

    async def handle_unsuppress(call: ServiceCall) -> None:
        rule_id: str = call.data[CONF_RULE_ID]
        engine = _resolve_engine(hass, rule_id)
        await engine.async_unsuppress()
        _LOGGER.info("Unsuppressed rule %s", engine.config.name)

    async def handle_clear_history(call: ServiceCall) -> None:
        rule_id: str = call.data[CONF_RULE_ID]
        engine = _resolve_engine(hass, rule_id)
        await engine.async_clear_history()
        _LOGGER.info("Cleared history for rule %s", engine.config.name)

    async def handle_list_rules(call: ServiceCall) -> ServiceResponse:
        rules: list[dict[str, Any]] = []
        for engine in _iter_engines(hass):
            config = engine.config
            rules.append(
                {
                    "rule_id": getattr(config, "unique_id", None),
                    "name": getattr(config, "name", None),
                    "target_entities": list(
                        getattr(config, "target_entities", []) or []
                    ),
                    "mode": getattr(config, "mode", None),
                    "status": getattr(engine, "status", None),
                    "enabled": getattr(engine, "enabled", None),
                    "suppressed_until": (
                        engine.suppressed_until.isoformat()
                        if getattr(engine, "suppressed_until", None) is not None
                        else None
                    ),
                }
            )
        return {"rules": rules}

    async def handle_panic_stop(call: ServiceCall) -> None:
        engines = _iter_engines(hass)
        for engine in engines:
            try:
                engine.enabled = False
            except AttributeError:
                set_enabled = getattr(engine, "async_set_enabled", None)
                if set_enabled is not None:
                    await set_enabled(False)
            await engine.async_reset_cooldowns()
            await engine.async_suppress(
                duration_minutes=PANIC_STOP_DURATION_MINUTES,
                user_id=call.context.user_id,
            )

        hass.data.setdefault(DOMAIN, {})["hub_master_enabled"] = False
        async_dispatcher_send(hass, SIGNAL_MASTER_UPDATED, False)
        _LOGGER.warning(
            "Entity Guard panic stop: disabled %d rule(s) and suppressed for %d min",
            len(engines),
            PANIC_STOP_DURATION_MINUTES,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SUPPRESS):
        hass.services.async_register(
            DOMAIN, SERVICE_SUPPRESS, handle_suppress, schema=SUPPRESS_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_UNSUPPRESS):
        hass.services.async_register(
            DOMAIN, SERVICE_UNSUPPRESS, handle_unsuppress, schema=UNSUPPRESS_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_CLEAR_HISTORY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_CLEAR_HISTORY,
            handle_clear_history,
            schema=CLEAR_HISTORY_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_LIST_RULES):
        hass.services.async_register(
            DOMAIN,
            SERVICE_LIST_RULES,
            handle_list_rules,
            schema=LIST_RULES_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_PANIC_STOP):
        hass.services.async_register(
            DOMAIN, SERVICE_PANIC_STOP, handle_panic_stop, schema=PANIC_STOP_SCHEMA
        )


@callback
def async_unload_services(hass: HomeAssistant) -> None:
    """Remove Entity Guard services."""
    for service in (
        SERVICE_SUPPRESS,
        SERVICE_UNSUPPRESS,
        SERVICE_CLEAR_HISTORY,
        SERVICE_LIST_RULES,
        SERVICE_PANIC_STOP,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
