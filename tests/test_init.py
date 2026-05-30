"""Tests for Entity Guard integration setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant

from custom_components.entity_guard import (
    PLATFORMS_HUB,
    PLATFORMS_RULE,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.entity_guard.const import DOMAIN


async def test_setup_hub_entry(hass: HomeAssistant, hub_entry) -> None:
    """Hub entry setup forwards to hub platforms."""
    hub_entry.add_to_hass(hass)
    with (
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ) as mock_forward,
        patch(
            "custom_components.entity_guard._async_install_card",
            new_callable=AsyncMock,
        ),
    ):
        result = await async_setup_entry(hass, hub_entry)

    assert result is True
    assert DOMAIN in hass.data
    mock_forward.assert_called_once_with(hub_entry, PLATFORMS_HUB)


async def test_setup_rule_entry(hass: HomeAssistant, rule_entry) -> None:
    """Rule entry setup forwards to rule platforms."""
    rule_entry.add_to_hass(hass)
    with (
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ) as mock_forward,
        patch(
            "custom_components.entity_guard._async_install_card",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.entity_guard.RuleEngine.async_setup",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.entity_guard.RuleEngine.async_unload",
            new_callable=AsyncMock,
        ),
    ):
        result = await async_setup_entry(hass, rule_entry)

    assert result is True
    mock_forward.assert_called_once_with(rule_entry, PLATFORMS_RULE)


async def test_unload_hub_entry(hass: HomeAssistant, hub_entry) -> None:
    """Hub entry unloads hub platforms."""
    hub_entry.add_to_hass(hass)
    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_unload:
        result = await async_unload_entry(hass, hub_entry)

    assert result is True
    mock_unload.assert_called_once_with(hub_entry, PLATFORMS_HUB)


async def test_unload_rule_entry(hass: HomeAssistant, rule_entry) -> None:
    """Rule entry unloads rule platforms."""
    rule_entry.add_to_hass(hass)
    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_unload:
        result = await async_unload_entry(hass, rule_entry)

    assert result is True
    mock_unload.assert_called_once_with(rule_entry, PLATFORMS_RULE)
