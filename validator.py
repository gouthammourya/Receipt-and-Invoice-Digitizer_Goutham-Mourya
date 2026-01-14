import re
from datetime import datetime

def validate_receipt(data: dict) -> list:
    """
    Soft validation:
    - Fix what we can
    - Warn only when data is unusable
    """
    errors = []

    # ---------- BASIC STRUCTURE ----------
    if not isinstance(data, dict):
        return ["Invalid receipt data structure"]

    # ---------- STORE ----------
    if not data.get("store"):
        data["store"] = "Unknown"

    # ---------- ITEMS ----------
    items = data.get("items", [])
    if not items or not isinstance(items, list):
        errors.append("No items detected")

    # ---------- NUMERIC SAFETY ----------
    subtotal = float(data.get("subtotal") or 0)
    tax = float(data.get("tax") or 0)
    total = float(data.get("total") or 0)

    # ---------- AUTO FIX TOTAL ----------
    if total <= 0:
        if subtotal > 0:
            data["total"] = round(subtotal + tax, 2)
        elif items:
            data["subtotal"] = round(sum(i["price"] for i in items), 2)
            data["total"] = round(data["subtotal"] + tax, 2)
        else:
            errors.append("Total amount is missing or invalid")

    # ---------- NEGATIVE CHECK ----------
    if data["total"] <= 0:
        errors.append("Total amount is invalid")

    return errors
