"""Tests for Entity Guard config flow (skeleton)."""
from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.entity_guard.const import (
    CONF_ENTRY_TYPE,
    DOMAIN,
    ENTRY_TYPE_HUB,
)


async def test_user_step_shows_menu(hass: HomeAssistant) -> None:
    """User step presents the rule/hub menu."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] == FlowResultType.MENU
    assert set(result["menu_options"]) == {"rule", "hub"}


async def test_hub_single_instance_aborts(hass: HomeAssistant, hub_entry) -> None:
    """A second hub setup attempt aborts."""
    hub_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "hub"}
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


@pytest.mark.skip(reason="pending integration: end-to-end rule flow exercises rule_engine")
async def test_create_state_rule_end_to_end(hass: HomeAssistant) -> None:
    """End-to-end: create a state-mode rule via the multi-step flow."""
