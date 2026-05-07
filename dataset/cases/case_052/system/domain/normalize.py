def _normalize_qty(raw_qty) -> int:
    qty = int(raw_qty)
    if qty <= 0:
        raise ValueError("qty must be > 0")
    return qty


def _normalize_unit_price(raw_price) -> float:
    unit_price = float(raw_price)
    if unit_price < 0:
        raise ValueError("unit_price must be >= 0")
    return unit_price


def normalize_order(order: dict) -> dict:
    return {
        "qty": _normalize_qty(order.get("qty", 1)),
        "unit_price": _normalize_unit_price(order.get("unit_price", 0.0)),
        "tier": str(order.get("tier", "none")).strip().lower(),
        "state": str(order.get("state", "")).strip().upper(),
    }
