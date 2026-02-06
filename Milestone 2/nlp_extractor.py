import spacy
import re
from datetime import datetime

nlp = spacy.load("en_core_web_sm")

def extract_fields_with_spacy(text: str) -> dict:
    doc = nlp(text)

    result = {
        "store": "Unknown",
        "date": "N/A",
        "time": "N/A",
        "payment": "N/A"
    }

    # -------- STORE (ORG entity) --------
    orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    if orgs:
        result["store"] = orgs[0]

    # -------- DATE --------
    dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    if dates:
        result["date"] = normalize_date(dates[0])

    # -------- TIME --------
    times = [ent.text for ent in doc.ents if ent.label_ == "TIME"]
    if times:
        result["time"] = times[0]

    # -------- PAYMENT MODE --------
    lower = text.lower()
    if "cash" in lower:
        result["payment"] = "Cash"
    elif "card" in lower or "visa" in lower or "mastercard" in lower:
        result["payment"] = "Card"
    elif "upi" in lower:
        result["payment"] = "UPI"

    return result


def normalize_date(raw: str) -> str:
    try:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(raw, fmt).strftime("%d/%m/%Y")
            except:
                continue
    except:
        pass
    return raw
