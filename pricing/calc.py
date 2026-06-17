"""
Price calculation engine.

The salesperson picks a cluster, product, type, diameter and segment; the engine
takes the base price from the active price list and layers the editable
components on top to produce a transparent, line-by-line Net Price.
"""
from __future__ import annotations

# Products map to the two price columns.
PRODUCTS = {
    "JSW One 550":   "fe550",   # Basic price + Frt (Gr. Fe-550)
    "JSW One 550 D": "fe550d",  # Fe 550D
}

DIAS = ["8", "10", "12-32"]          # 12-32 mm is the list base (no dia extra)
SEGMENTS = ["retail", "project"]
TYPES = ["Straight", "Bend"]

# Component sign convention for building the Net Price.
#   +1  => added to the price
#   -1  => deducted from the price
# A user can always enter a negative number to flip the effect for one quote.
COMPONENTS = [
    ("freight_to_dealer",        "Freight to Dealer",        +1),
    ("jsw_one_ecp",              "JSW One ECP",              +1),
    ("cash_discount",            "Cash Discount (CD)",       -1),
    ("distributor_margin",       "Distributor's Margin",     -1),
    ("additional_price_support", "Additional Price Support", -1),
    ("company_scheme",           "Company Scheme",           -1),
    ("distributor_scheme",       "Distributor Scheme",       -1),
]


def dia_extra(pl: dict, dia: str, segment: str) -> float:
    """Diameter add-on (Rs/MT) from the price list for the given segment."""
    if dia == "8":
        return pl["dia8_project"] if segment == "project" else pl["dia8_retail"]
    if dia == "10":
        return pl["dia10_project"] if segment == "project" else pl["dia10_retail"]
    return 0.0  # 12-32 mm is the base


def base_price(pl: dict, price_row: dict, product: str, dia: str,
               segment: str, btype: str) -> dict:
    """Build the base price (before components) with a breakdown."""
    col = PRODUCTS[product]
    list_price = price_row.get(col)
    if list_price is None:
        return {"available": False, "list_price": None}

    de = dia_extra(pl, dia, segment)
    bend = pl["bend_extra"] if btype == "Bend" else 0.0
    base = list_price + de + bend
    return {
        "available": True,
        "list_price": float(list_price),
        "dia_extra": float(de),
        "bend_extra": float(bend),
        "base": float(base),
    }


def net_price(base: float, components: dict) -> dict:
    """Apply components to a base price; return total + signed line items."""
    lines = []
    total = base
    for field, label, sign in COMPONENTS:
        val = float(components.get(field, 0) or 0)
        effect = sign * val
        total += effect
        lines.append({"field": field, "label": label, "sign": sign,
                      "value": val, "effect": effect})
    return {"base": base, "lines": lines, "net": total}


def incentive_for(achievement_pct: float, tiers: list[dict]) -> dict | None:
    """Highest incentive tier whose threshold the achievement % meets."""
    best = None
    for t in sorted(tiers, key=lambda x: x["min_pct"]):
        if achievement_pct >= t["min_pct"]:
            best = t
    return best


def blended_rate(pl: dict, price_row: dict, product: str, segment: str,
                 btype: str, mix: dict[str, float]) -> dict | None:
    """Weighted-average base price across a diameter mix.

    mix: {"8": pct, "10": pct, "12-32": pct} (percentages, need not sum to 100;
    they are normalised). Returns None if the product price is unavailable.
    """
    col = PRODUCTS[product]
    if price_row.get(col) is None:
        return None
    total_w = sum(max(0.0, v) for v in mix.values())
    if total_w <= 0:
        return None
    rate = 0.0
    parts = []
    for dia, pct in mix.items():
        w = max(0.0, pct) / total_w
        if w == 0:
            continue
        b = base_price(pl, price_row, product, dia, segment, btype)["base"]
        rate += w * b
        parts.append({"dia": dia, "weight_pct": w * 100, "base": b})
    return {"blended": rate, "parts": parts}
