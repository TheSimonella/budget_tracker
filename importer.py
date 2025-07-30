import csv
from io import TextIOWrapper

from sqlalchemy import func

from app import db, Category, Transaction, validate_amount, validate_date

# Possible header names for common fields
HEADER_ALIASES = {
    "date": ["date", "transaction date", "posted", "posted date"],
    "amount": ["amount", "debit", "credit", "transaction amount"],
    "description": ["description", "details", "memo"],
    "merchant": ["merchant", "payee"],
    "category": ["category", "classification", "type"],
    "transaction_type": ["transaction type", "tx_type"],
}

# Keyword mapping for heuristic category inference
KEYWORD_CATEGORIES = {
    "gas": "Gas",
    "shell": "Gas",
    "amazon": "Shopping",
    "target": "Groceries",
    "netflix": "Entertainment",
    "uber": "Transportation",
}


def _normalize(s: str) -> str:
    return s.strip().lower() if s else ""


def _detect_headers(fieldnames, custom_map=None):
    """Return a mapping of internal field names to CSV headers."""
    mapping = {}
    normalized = { _normalize(h): h for h in fieldnames }
    for field, aliases in HEADER_ALIASES.items():
        names = aliases[:]
        if custom_map and field in custom_map:
            names = custom_map[field] + names
        for name in names:
            key = _normalize(name)
            if key in normalized:
                mapping[field] = normalized[key]
                break
    return mapping


def _guess_category(cat_str, text):
    if cat_str:
        cat = Category.query.filter(func.lower(Category.name) == cat_str.lower()).first()
        if cat:
            return cat
    combined = text.lower()
    for kw, name in KEYWORD_CATEGORIES.items():
        if kw.lower() in combined:
            cat = Category.query.filter(func.lower(Category.name) == name.lower()).first()
            if cat:
                return cat
    return None


def parse_csv(file_obj, column_map=None):
    """Parse a CSV file object and return (transactions, unresolved_rows)."""
    if hasattr(file_obj, "stream"):
        # Werkzeug FileStorage
        fh = TextIOWrapper(file_obj.stream, encoding="utf-8-sig")
    else:
        fh = TextIOWrapper(file_obj, encoding="utf-8-sig")
    reader = csv.DictReader(fh)
    header_map = _detect_headers(reader.fieldnames, column_map)

    transactions = []
    unresolved = []
    row_num = 1
    amount_header = header_map.get("amount", "").lower()

    for row in reader:
        row_num += 1
        get = lambda f: row.get(header_map.get(f, ""), "").strip()
        date_str = get("date")
        amt_str = get("amount")
        desc = get("description") or None
        merchant = get("merchant") or None
        cat_str = get("category")
        tx_type_raw = get("transaction_type")

        amount_val = None
        amount_error = None
        try:
            amount_val = float(amt_str.replace("$", "").replace(",", ""))
        except ValueError:
            amount_error = "Invalid amount format"

        if tx_type_raw:
            low = tx_type_raw.lower()
            if "income" in low or "credit" in low or "deposit" in low:
                tx_type = "income"
            elif "withdraw" in low or "debit" in low or "expense" in low:
                tx_type = "expense"
            else:
                tx_type = low
        else:
            if amount_header.startswith("debit") or amount_val and amount_val < 0:
                tx_type = "expense"
            elif amount_header.startswith("credit"):
                tx_type = "income"
            else:
                tx_type = "income" if amount_val and amount_val >= 0 else "expense"

        if amount_val is not None:
            amt, err = validate_amount(abs(amount_val))
            amount_error = amount_error or err
        else:
            amt, err = (None, "Invalid amount format")
            amount_error = amount_error or err

        date_val, date_error = validate_date(date_str)

        category = _guess_category(cat_str, f"{desc or ''} {merchant or ''}")

        if amount_error or date_error or not category:
            unresolved.append({
                "row": row_num,
                "data": row,
                "error": amount_error or date_error or "Unknown category"
            })
            continue

        transactions.append(Transaction(
            amount=amt,
            transaction_type=tx_type,
            category_id=category.id,
            description=desc or "",
            merchant=merchant or "",
            date=date_val,
            notes=""
        ))

    return transactions, unresolved
