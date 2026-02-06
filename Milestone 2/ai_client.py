import re
import json
import requests
import spacy
from typing import Dict, List

# ---------------- CONFIG ----------------
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

nlp = spacy.load("en_core_web_sm")

# ---------------- REGEX ----------------

PRICE_RE = re.compile(r"\$?\s*(\d+\.\d{2})")

DATE_RE = re.compile(
    r"(\d{2}[-/]\w{3}[-/]\d{4}|\d{2}/\d{2}/\d{4})",
    re.I
)

TIME_RE = re.compile(
    r"(\d{1,2}:\d{2}:\d{2})\s*([APMapm]?)"
)

INVALID_ITEM_WORDS = {
    "%", "tax", "total", "subtotal", "change", "cash", "visa", "master"
}

# ---------------- ITEM EXTRACTION ----------------

def extract_items_prices(text: str) -> List[Dict]:
    """
    Robust receipt line-item extractor.
    Handles quantity, currency symbols, OCR noise.
    """
    items = []
    seen = set()

    BAD_WORDS = {
        "subtotal", "total", "tax", "change", "cash",
        "visa", "master", "balance", "amount", "%"
    }

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if len(line) < 5:
            continue

        # Look for price at END of line
        price_match = re.search(r"(\$?\s*\d+\.\d{2})\s*$", line)
        if not price_match:
            continue

        price = float(re.sub(r"[^\d.]", "", price_match.group(1)))

        # Extract item name part
        name_part = line[:price_match.start()].strip()

        # Remove leading quantity (e.g. "2 Taco")
        name_part = re.sub(r"^\d+\s+", "", name_part)

        # Clean OCR junk
        name = re.sub(r"[^A-Za-z\s]", "", name_part).strip()

        lname = name.lower()

        # Semantic filtering
        if (
            not name
            or len(name) < 3
            or any(bad in lname for bad in BAD_WORDS)
        ):
            continue

        # De-duplicate
        key = f"{lname}-{price}"
        if key in seen:
            continue

        seen.add(key)
        items.append({
            "name": name.title(),
            "price": round(price, 2)
        })

    return items

# ---------------- TOTALS ----------------

def extract_totals(text: str):
    subtotal = tax = total = 0.0

    for line in text.splitlines():
        low = line.lower()
        prices = PRICE_RE.findall(line)
        if not prices:
            continue

        value = float(prices[-1])

        if "subtotal" in low:
            subtotal = value
        elif "tax" in low:
            tax = value
        elif "total" in low and "subtotal" not in low:
            total = value

    return subtotal, tax, total


# ---------------- STORE / DATE / TIME / PAYMENT ----------------

def extract_store_date_payment(text: str):
    store = "Unknown"
    date = "N/A"
    time = "N/A"
    payment = "N/A"

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # Store name
    for l in lines[:5]:
        if not re.search(r"\d", l) and len(l) > 4:
            store = l.title()
            break

    # Date
    m = DATE_RE.search(text)
    if m:
        date = m.group(1)

    # Time
    m = TIME_RE.search(text)
    if m:
        t = m.group(1)
        suffix = m.group(2).upper()
        if suffix == "P":
            suffix = "PM"
        elif suffix == "A":
            suffix = "AM"
        time = f"{t} {suffix}".strip()

    # Payment
    clean = re.sub(r"[^a-zA-Z ]", " ", text.lower())
    if "cash" in clean:
        payment = "Cash"
    elif any(k in clean for k in ["visa", "master", "card", "debit", "credit"]):
        payment = "Card"

    return store, date, time, payment


# ---------------- AI CLEANUP ONLY ----------------

def normalize_with_ai(data: Dict) -> Dict:
    try:
        prompt = f"""
Fix spelling only. Do NOT invent data.
Return valid JSON only.

DATA:
{json.dumps(data, indent=2)}
"""
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "temperature": 0.0,
                "stream": False
            },
            timeout=20
        )

        match = re.search(r"\{[\s\S]*\}", r.json().get("response", ""))
        return json.loads(match.group()) if match else data

    except Exception:
        return data


# ---------------- MAIN ----------------

def extract_and_map(ocr_text: str) -> Dict:
    if len(ocr_text.strip()) < 40:
        raise ValueError("OCR text too weak")

    items = extract_items_prices(ocr_text)
    subtotal, tax, total = extract_totals(ocr_text)
    store, date, time, payment = extract_store_date_payment(ocr_text)

    if subtotal == 0 and items:
        subtotal = round(sum(i["price"] for i in items), 2)

    if total == 0:
        total = round(subtotal + tax, 2)

    base = {
        "store": store,
        "date": date,
        "time": time,
        "payment": payment,
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
        "items": items
    }

    return normalize_with_ai(base)
