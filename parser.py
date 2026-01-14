import re


def safe_float(match_list, default=0.0):
    try:
        return float(match_list[0])
    except Exception:
        return default


def parse_receipt(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    store = "Unknown"
    date = "N/A"
    time = "N/A"
    payment = "N/A"

    subtotal = 0.0
    tax = 0.0
    total = 0.0
    items = []
    seen = set()

    # Store name
    for l in lines[:5]:
        if not re.search(r"\d", l) and len(l) > 3:
            store = l
            break

    for l in lines:
        low = l.lower()

        if "subtotal" in low:
            subtotal = safe_float(re.findall(r"\d+\.\d{2}", l))
            continue

        if "tax" in low:
            tax += safe_float(re.findall(r"\d+\.\d{2}", l))
            continue

        if re.search(r"\b(total|grand total)\b", low):
            total = safe_float(re.findall(r"\d+\.\d{2}", l))
            continue

        # Item line
        m = re.match(r"(.+?)\s+(\d+\.\d{2})$", l)
        if m:
            name = m.group(1).strip()
            price = float(m.group(2))

            if any(x in name.lower() for x in ["tax", "total", "subtotal", "change"]):
                continue

            key = f"{name}-{price}"
            if key not in seen:
                seen.add(key)
                items.append({
                    "name": name,
                    "price": round(price, 2)
                })

    # Final safety fixes
    if subtotal == 0.0 and items:
        subtotal = round(sum(i["price"] for i in items), 2)

    if total == 0.0:
        total = round(subtotal + tax, 2)

    return {
        "store": store,
        "date": date,
        "time": time,
        "payment": payment,
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
        "items": items
    }
