def compute_total(order: dict) -> float:
    subtotal = order["qty"] * order["unit_price"]
    discount = tier_discount(subtotal=subtotal, tier=order["tier"])
    tax = tax_amount(subtotal=subtotal, state=order["state"])
    return round(subtotal - discount + tax, 2)


def tier_discount(subtotal: float, tier: str) -> float:
    rates = {"none": 0.0, "silver": 0.05, "gold": 0.10}
    if tier not in rates:
        raise ValueError("unknown tier")
    return subtotal * rates[tier]


def tax_amount(subtotal: float, state: str) -> float:
    rates = {"CA": 0.10, "WA": 0.09, "OR": 0.00}
    return subtotal * rates.get(state, 0.08)
