import requests
import json
import re
from typing import Dict, List

# ---------------- OLLAMA CONFIG ----------------
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"   # You can also try: mistral, phi3


# ---------------- JSON SAFETY ----------------
def _safe_json_extract(text: str) -> Dict:
    """
    Extract and safely parse JSON returned by local LLM.
    Repairs common formatting issues.
    """
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON found in AI output")

    json_text = match.group()

    # Fix common JSON issues
    json_text = re.sub(r",\s*}", "}", json_text)
    json_text = re.sub(r",\s*]", "]", json_text)

    return json.loads(json_text)


def _normalize_items(items: List[Dict]) -> List[Dict]:
    """
    Clean and normalize item names and prices.
    """
    cleaned = []
    seen = set()

    for it in items:
        name = str(it.get("name", "")).strip()
        price = it.get("price", 0)

        if not name:
            continue

        try:
            price = float(price)
        except Exception:
            continue

        lname = name.lower()

        # Remove non-item lines
        if any(k in lname for k in ["tax", "total", "subtotal", "service", "tip", "change"]):
            continue

        # Remove quantities (e.g. "2 Coffee")
        name = re.sub(r"^\d+\s*", "", name)

        key = f"{name.lower()}-{price}"
        if key not in seen:
            seen.add(key)
            cleaned.append({
                "name": name,
                "price": round(price, 2)
            })

    return cleaned


# ---------------- MAIN FUNCTION ----------------
def extract_and_map(ocr_text: str) -> Dict:
    """
    Uses local Ollama LLM to map OCR text into structured receipt data.
    """

    # Guardrail: avoid AI for very weak OCR
    if len(ocr_text.strip()) < 120:
        raise ValueError("OCR text too small for AI")

    prompt = f"""
You are a receipt understanding AI.

TASK:
Convert OCR text into structured JSON.

STRICT RULES:
- Output ONLY valid JSON
- No explanations
- No markdown
- No extra text

SCHEMA:
{{
  "store": "string",
  "date": "string or N/A",
  "time": "string or N/A",
  "payment": "Cash/Card/N/A",
  "subtotal": number,
  "tax": number,
  "total": number,
  "items": [
    {{ "name": "string", "price": number }}
  ]
}}

IMPORTANT RULES:
- Fix OCR errors in item names (PhoGa → Pho Ga)
- Remove quantities from names
- DO NOT include subtotal/tax/total/service as items
- Remove duplicate items
- If subtotal missing, compute from items
- Total must be >= subtotal + tax
- If date/time unclear, return "N/A"

OCR TEXT:
\"\"\"
{ocr_text}
\"\"\"
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "temperature": 0.1,
            "stream": False
        },
        timeout=60
    )

    raw = response.json().get("response", "")
    data = _safe_json_extract(raw)

    # ---------------- POST PROCESSING ----------------
    items = _normalize_items(data.get("items", []))

    subtotal = float(data.get("subtotal", 0) or 0)
    tax = float(data.get("tax", 0) or 0)
    total = float(data.get("total", 0) or 0)

    # Fix subtotal
    if subtotal <= 0 and items:
        subtotal = round(sum(i["price"] for i in items), 2)

    # Fix total
    if total <= 0 or total < subtotal:
        total = round(subtotal + tax, 2)

    return {
        "store": data.get("store", "Unknown").strip() or "Unknown",
        "date": data.get("date", "N/A"),
        "time": data.get("time", "N/A"),
        "payment": data.get("payment", "N/A"),
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
        "items": items
    }
