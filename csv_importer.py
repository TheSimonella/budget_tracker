"""CSV Importer for bank transactions.

This module provides utilities to parse bank transaction
strings, extract merchant information, and categorize
transactions using simple keyword matching.
"""

from __future__ import annotations

import csv
import re
from typing import Dict, List, Optional

# --- simple categorization ---
CATEGORY_KEYWORDS: Dict[str, str] = {
    'GROCERY': 'Groceries',
    'WALMART': 'Groceries',
    'KROGER': 'Groceries',
    'SAFEWAY': 'Groceries',
    'EXXON': 'Gas',
    'SHELL': 'Gas',
    'CHEVRON': 'Gas',
    'RENT': 'Rent/Mortgage',
    'MORTGAGE': 'Rent/Mortgage',
    'UTILITIES': 'Utilities',
    'INTERNET': 'Internet',
    'COMCAST': 'Internet',
    'PHONE': 'Phone',
}


def categorize_merchant(merchant: str) -> Optional[str]:
    upper = merchant.upper()
    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword in upper:
            return category
    return None


# --- text parsing helpers (adapted from banking-class repository) ---
STATES_RE = re.compile(
    r'(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|'
    r'NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)$'
)

THIRD_PARTIES_RE = re.compile(r'^(...?\*|LEVELUP\*|PAYPAL \*)')


def parse_description(raw: str) -> Dict[str, Optional[str]]:
    """Parse a raw transaction description into components."""
    desc = raw
    time = None
    date = None
    phone = None
    country = None
    state = None

    m = re.search(r'([0-9]{2}:[0-9]{2}:[0-9]{2})', desc)
    if m:
        time = m.group(1)
        desc = re.sub(r'([0-9]{2}:[0-9]{2}:[0-9]{2})', '', desc, count=1)

    m = re.search(r'([0-1][0-9]/[0-3][0-9])', desc)
    if m:
        date = m.group(1)
        desc = re.sub(r'([0-1][0-9]/[0-3][0-9])', '', desc, count=1)

    desc = re.sub('Branch Cash Withdrawal', '', desc, flags=re.IGNORECASE)

    m = re.search(r'([0-9]{3}-[0-9]{3}-[0-9]{4})', desc)
    if m:
        phone = m.group(1)
        desc = re.sub(r'([0-9]{3}-[0-9]{3}-[0-9]{4})', '', desc, count=1)

    desc = desc.strip()
    desc = re.sub(r'^POS ', '', desc)

    m = re.search(r'(US)$', desc)
    if m:
        country = m.group(1)
        desc = re.sub(r'(US)$', '', desc).strip()

    m = STATES_RE.search(desc)
    if m:
        state = m.group(1)
        desc = STATES_RE.sub('', desc).strip()

    merchant = desc.upper()
    merchant = THIRD_PARTIES_RE.sub('', merchant)
    merchant = re.sub(r'\s\s+.+$', '', merchant)
    merchant = merchant.strip()
    merchant = re.sub(r'X+-?X+', '', merchant)
    merchant = re.sub(r'( ID:.*| PAYMENT ID:.*| PMT ID:.*)', '', merchant)
    merchant = merchant.strip()
    merchant = re.sub(r'[#]?[ ]?([0-9]){1,999}$', '', merchant)
    merchant = merchant.strip()
    merchant = re.sub(r'([ ]?-[ ]?|[_])', '', merchant)
    merchant = merchant.strip()
    merchant = re.sub(r'[.]com.*$', '', merchant)
    merchant = merchant.strip()
    merchant = re.sub(r' .$', '', merchant)
    merchant = merchant.strip()
    if merchant == '':
        merchant = ' '

    return {
        'description': desc.strip(),
        'time': time,
        'date': date,
        'phone': phone,
        'country': country,
        'state': state,
        'merchant': merchant,
    }


def import_csv(path: str) -> List[Dict[str, Optional[str]]]:
    """Import CSV of transactions. Expected columns: raw, amount."""
    results: List[Dict[str, Optional[str]]] = []
    with open(path, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                raise ValueError('CSV must have at least two columns')
            raw, amount = row[0], row[1]
            parsed = parse_description(raw)
            merchant = parsed['merchant'] or ''
            category = categorize_merchant(merchant) or 'Uncategorized'
            results.append({
                'date': parsed['date'],
                'merchant': merchant,
                'amount': float(amount),
                'category_guess': category,
            })
    return results
