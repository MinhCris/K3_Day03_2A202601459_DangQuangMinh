"""Deterministic e-commerce tools used in the ReAct lab scenario.

The data is intentionally local and predictable so students can test agent
reasoning without an API key or external service.
"""

import math
from typing import Any, Dict, List


CATALOG: Dict[str, Dict[str, Any]] = {
    "iphone 15": {
        "display_name": "iPhone 15",
        "available_quantity": 5,
        "unit_price_vnd": 22_990_000,
        "unit_weight_kg": 0.171,
    },
    "macbook air m2": {
        "display_name": "MacBook Air M2",
        "available_quantity": 2,
        "unit_price_vnd": 26_990_000,
        "unit_weight_kg": 1.24,
    },
    "airpods pro 2": {
        "display_name": "AirPods Pro 2",
        "available_quantity": 12,
        "unit_price_vnd": 6_190_000,
        "unit_weight_kg": 0.051,
    },
}

COUPONS = {
    "WINNER": 10.0,
    "STUDENT": 5.0,
    "WELCOME": 3.0,
}

SHIPPING_ZONES = {
    "hanoi": {"display_name": "Hanoi", "base_fee_vnd": 30_000, "extra_kg_fee_vnd": 15_000},
    "ho chi minh city": {"display_name": "Ho Chi Minh City", "base_fee_vnd": 35_000, "extra_kg_fee_vnd": 18_000},
    "da nang": {"display_name": "Da Nang", "base_fee_vnd": 40_000, "extra_kg_fee_vnd": 20_000},
}


def _normalise(value: str) -> str:
    return " ".join(value.strip().lower().split())


def check_stock(item_name: str) -> Dict[str, Any]:
    """Return stock, price, and weight for an exact catalog product name."""
    if not isinstance(item_name, str) or not item_name.strip():
        raise ValueError("item_name must be a non-empty string")

    product = CATALOG.get(_normalise(item_name))
    if product is None:
        return {
            "found": False,
            "message": f"No catalog product matches '{item_name}'.",
            "available_products": [product["display_name"] for product in CATALOG.values()],
        }
    return {"found": True, **product}


def get_discount(coupon_code: str) -> Dict[str, Any]:
    """Look up a coupon and return its percentage discount (zero if invalid)."""
    if not isinstance(coupon_code, str) or not coupon_code.strip():
        raise ValueError("coupon_code must be a non-empty string")

    code = coupon_code.strip().upper()
    percent = COUPONS.get(code, 0.0)
    return {
        "coupon_code": code,
        "valid": code in COUPONS,
        "discount_percent": percent,
        "message": "Coupon applied." if code in COUPONS else "Coupon is invalid; no discount applied.",
    }


def calc_shipping(weight_kg: float, destination: str) -> Dict[str, Any]:
    """Calculate domestic shipping from package weight and destination city."""
    if not isinstance(weight_kg, (int, float)) or isinstance(weight_kg, bool) or weight_kg <= 0:
        raise ValueError("weight_kg must be a positive number")
    if not isinstance(destination, str) or not destination.strip():
        raise ValueError("destination must be a non-empty string")

    zone = SHIPPING_ZONES.get(_normalise(destination))
    if zone is None:
        return {
            "supported": False,
            "message": f"Shipping to '{destination}' is not supported.",
            "supported_destinations": [zone["display_name"] for zone in SHIPPING_ZONES.values()],
        }

    additional_kg = max(0, math.ceil(float(weight_kg) - 1))
    shipping_fee = zone["base_fee_vnd"] + additional_kg * zone["extra_kg_fee_vnd"]
    return {
        "supported": True,
        "destination": zone["display_name"],
        "weight_kg": round(float(weight_kg), 3),
        "shipping_fee_vnd": shipping_fee,
    }


def calculate_order_total(
    unit_price_vnd: float,
    quantity: int,
    discount_percent: float = 0,
    shipping_fee_vnd: float = 0,
) -> Dict[str, Any]:
    """Calculate a transparent order total after percentage discount and shipping."""
    if not isinstance(unit_price_vnd, (int, float)) or unit_price_vnd < 0:
        raise ValueError("unit_price_vnd must be a non-negative number")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
        raise ValueError("quantity must be a positive integer")
    if not isinstance(discount_percent, (int, float)) or not 0 <= discount_percent <= 100:
        raise ValueError("discount_percent must be between 0 and 100")
    if not isinstance(shipping_fee_vnd, (int, float)) or shipping_fee_vnd < 0:
        raise ValueError("shipping_fee_vnd must be a non-negative number")

    subtotal = round(unit_price_vnd * quantity)
    discount_amount = round(subtotal * discount_percent / 100)
    total = round(subtotal - discount_amount + shipping_fee_vnd)
    return {
        "subtotal_vnd": subtotal,
        "discount_percent": discount_percent,
        "discount_amount_vnd": discount_amount,
        "shipping_fee_vnd": round(shipping_fee_vnd),
        "total_vnd": total,
    }


def get_ecommerce_tools() -> List[Dict[str, Any]]:
    """Return concise, LLM-facing specifications and handlers for all tools."""
    return [
        {
            "name": "check_stock",
            "description": (
                "Get stock, unit price in VND, and unit weight in kg for one exact product. "
                "Input: {\"item_name\": \"iPhone 15\"}."
            ),
            "func": check_stock,
        },
        {
            "name": "get_discount",
            "description": (
                "Validate a coupon and get its discount percentage. "
                "Input: {\"coupon_code\": \"WINNER\"}."
            ),
            "func": get_discount,
        },
        {
            "name": "calc_shipping",
            "description": (
                "Calculate shipping in VND for a positive package weight and a supported city "
                "(Hanoi, Ho Chi Minh City, Da Nang). Input: {\"weight_kg\": 0.342, \"destination\": \"Hanoi\"}."
            ),
            "func": calc_shipping,
        },
        {
            "name": "calculate_order_total",
            "description": (
                "Calculate subtotal, discount amount, and final total in VND. "
                "Input: {\"unit_price_vnd\": 22990000, \"quantity\": 2, "
                "\"discount_percent\": 10, \"shipping_fee_vnd\": 30000}."
            ),
            "func": calculate_order_total,
        },
    ]
