def quote(order: dict) -> float:
    qty = int(order.get("qty", 1))
    if qty <= 0:
        raise ValueError("qty must be > 0")
    unit_price = float(order.get("unit_price", 0.0))
    tier = str(order.get("tier", "none")).strip().lower()
    state = str(order.get("state", "")).strip().upper()

    subtotal = qty * unit_price
    tier_discount = {"none": 0.0, "silver": 0.05, "gold": 0.10}.get(tier, None)
    if tier_discount is None:
        raise ValueError("unknown tier")
    discounted = subtotal * (1.0 - tier_discount)
    tax_rate = {"CA": 0.10, "WA": 0.09, "OR": 0.00}.get(state, 0.08)
    total = discounted * (1.0 + tax_rate)
    return round(total, 2)
