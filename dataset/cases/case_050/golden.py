def apply_discount(price: float, discount_pct: float) -> float:
    if not (0 <= discount_pct <= 100):
        raise ValueError("Discount must be 0-100")
    discount = price * discount_pct / 100
    return price - discount
