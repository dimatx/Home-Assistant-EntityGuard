"""Error-branch coverage tests for services.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.entity_guard.const import DOMAIN
from custom_components.entity_guard.services import async_register_services


def _make_engine_with_failure(method: str, exc: Exception):
    eng = MagicMock()
    eng.config.unique_id = "rule-1"
    eng.config.name = "Test"
    eng.async_suppress = AsyncMock()
    eng.async_unsuppress = AsyncMock()
    eng.async_clear_history = AsyncMock()
    eng.async_reset_cooldowns = AsyncMock()
    eng.set_enabled = MagicMock()
    getattr(eng, method).side_effect = exc
    return eng


def _inject(hass: HomeAssistant, eng):
    hass.data.setdefault(DOMAIN, {})["engines"] = {eng.config.unique_id: eng}


async def test_suppress_engine_raises(hass: HomeAssistant):
    eng = _make_engine_with_failure("async_suppress", RuntimeError("boom"))
    _inject(hass, eng)
    await async_register_services(hass)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "suppress",
            {"rule_id": "rule-1", "duration_minutes": 5},
            blocking=True,
        )


async def test_unsuppress_engine_raises(hass: HomeAssistant):
    eng = _make_engine_with_failure("async_unsuppress", RuntimeError("boom"))
    _inject(hass, eng)
    await async_register_services(hass)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, "unsuppress", {"rule_id": "rule-1"}, blocking=True
        )


async def test_clear_history_engine_raises(hass: HomeAssistant):
    eng = _make_engine_with_failure("async_clear_history", RuntimeError("boom"))
    _inject(hass, eng)
    await async_register_services(hass)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, "clear_history", {"rule_id": "rule-1"}, blocking=True
        )


async def test_panic_stop_partial_failure(hass: HomeAssistant):
    eng = _make_engine_with_failure("async_suppress", RuntimeError("boom"))
    _inject(hass, eng)
    await async_register_services(hass)
    # Should NOT raise — failures are logged as warnings
    await hass.services.async_call(DOMAIN, "panic_stop", {}, blocking=True)
    assert hass.data[DOMAIN]["hub_master_enabled"] is False
