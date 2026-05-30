"""Sanity tests for const module."""
from __future__ import annotations

from custom_components.entity_guard import const


def test_domain() -> None:
    assert const.DOMAIN == "entity_guard"


def test_status_values_count() -> None:
    assert len(const.STATUS_VALUES) == 6
    # Status set is exactly the documented six.
    assert set(const.STATUS_VALUES) == {
        const.STATUS_DISABLED,
        const.STATUS_SUPPRESSED,
        const.STATUS_ENFORCING,
        const.STATUS_COOLDOWN,
        const.STATUS_ARMED,
        const.STATUS_IDLE,
    }


def test_supported_operators_excludes_equality() -> None:
    assert "==" not in const.SUPPORTED_OPERATORS
    assert "!=" not in const.SUPPORTED_OPERATORS
    assert set(const.SUPPORTED_OPERATORS) == {"<", "<=", ">", ">="}


def test_entry_types() -> None:
    assert const.ENTRY_TYPE_HUB != const.ENTRY_TYPE_RULE
