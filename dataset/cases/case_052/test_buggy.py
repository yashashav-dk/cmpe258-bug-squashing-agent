import pytest

from buggy import quote


def test_gold_tier_with_tax():
    order = {"qty": "3", "unit_price": "10.0", "tier": "gold", "state": "ca"}
    assert quote(order) == 29.7


def test_silver_no_tax_state():
    order = {"qty": "1", "unit_price": "100.0", "tier": "silver", "state": "OR"}
    assert quote(order) == 95.0


def test_invalid_tier_raises():
    with pytest.raises(ValueError):
        quote({"qty": "2", "unit_price": "10", "tier": "platinum", "state": "WA"})
