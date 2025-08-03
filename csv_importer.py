"""CSV Importer for bank transactions.

This module provides utilities to parse bank transaction
strings, extract merchant information, and categorize
transactions using simple keyword matching.
"""

from __future__ import annotations

import csv
import re
from typing import Dict, List, Optional, Set, Tuple

from categories import categorize_merchant


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


def _skip_leading_empty(f, limit: int = 10) -> None:
    """Advance file iterator to the first potential header line.

    Many bank CSV exports start with a few blank or informational lines before
    the actual header row.  This helper scans the first ``limit`` lines and
    positions the file handle at the first line that appears to contain delimited
    data (at least one comma/semicolon/tab).
    """

    start = f.tell()
    delimiters = ",;\t"
    for _ in range(limit):
        pos = f.tell()
        line = f.readline()
        if line == "":
            break
        stripped = line.strip()
        if not stripped:
            continue
        if all(ch in ',"' for ch in stripped):
            continue
        if not any(d in line for d in delimiters):
            continue
        f.seek(pos)
        return
    # If no suitable line found within limit, reset to start so caller can
    # handle the lack of data gracefully.
    f.seek(start)


DESC_FIELDS = {'description', 'desc', 'payee', 'memo', 'name', 'action'}
AMOUNT_FIELDS = {'amount', 'amt', 'transaction amount', 'debit', 'credit'}
DATE_FIELDS = {
    'date',
    'transaction date',
    'post date',
    'posted date',
    'posting date',
    'date posted',
    'run date',
    'settlement date',
}


def import_csv(path: str) -> Tuple[List[Dict[str, Optional[str]]], Set[str]]:
    """Import CSV of transactions.

    Returns a tuple of (rows, unknown_merchants).
    """

    results: List[Dict[str, Optional[str]]] = []
    unknown_merchants: Set[str] = set()
    with open(path, newline='') as f:
        _skip_leading_empty(f)
        start_pos = f.tell()
        sample = f.read(2048)
        f.seek(start_pos)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        header_missing = False
        if reader.fieldnames and len(reader.fieldnames) > 1:
            try:
                float(reader.fieldnames[1].replace('$', '').replace(',', ''))
                header_missing = True
            except Exception:
                header_missing = False
        if header_missing or not reader.fieldnames or len(reader.fieldnames) < 2:
            f.seek(start_pos)
            reader = None
        if reader and reader.fieldnames:
            lower_fields = [h.lower().strip() for h in reader.fieldnames]
            desc_field = None
            amount_field = None
            debit_field = None
            credit_field = None
            date_field = None
            for name in reader.fieldnames:
                lname = name.lower().strip()
                if not desc_field and (lname in DESC_FIELDS or 'description' in lname):
                    desc_field = name
                if not amount_field and ('amount' in lname or lname in AMOUNT_FIELDS):
                    if lname == 'debit':
                        debit_field = name
                    elif lname == 'credit':
                        credit_field = name
                    else:
                        amount_field = name
                if not date_field and ('date' in lname or lname in DATE_FIELDS):
                    date_field = name
            if not desc_field:
                desc_field = reader.fieldnames[0]
            if not amount_field and not (debit_field or credit_field):
                # fall back to second column if amount fields not found
                amount_field = reader.fieldnames[1] if len(reader.fieldnames) > 1 else None
            if amount_field is None and not (debit_field or credit_field):
                raise ValueError('CSV must have at least two columns')

            for row in reader:
                if not any(row.values()):
                    continue
                raw = (row.get(desc_field) or '').strip()
                if debit_field or credit_field:
                    debit = (row.get(debit_field) or '').strip()
                    credit = (row.get(credit_field) or '').strip()
                    amount_str = credit or debit
                    if debit:
                        amount_str = '-' + debit.lstrip('-')
                else:
                    amount_str = (row.get(amount_field) or '').strip()
                if not raw or not amount_str:
                    continue
                amount_str = amount_str.replace('$', '').replace(',', '')
                amount_str = amount_str.replace('(', '-').replace(')', '')
                try:
                    amount = float(amount_str)
                except ValueError:
                    # skip rows where amount is not numeric
                    continue
                parsed = parse_description(raw)
                merchant = parsed['merchant'] or ''
                category = categorize_merchant(merchant)
                if not category:
                    unknown_merchants.add(merchant)
                    category = 'Uncategorized'
                date = row.get(date_field) if date_field else parsed['date']
                results.append({
                    'date': date,
                    'merchant': merchant,
                    'amount': amount,
                    'category_guess': category,
                })
        else:
            # No header; fall back to simple reader
            f.seek(start_pos)
            reader2 = csv.reader(f, dialect=dialect)
            for row in reader2:
                if not row or all(not c.strip() for c in row):
                    continue
                if len(row) < 2:
                    continue
                raw, amount_str = row[0], row[1]
                amount_str = amount_str.replace('$', '').replace(',', '')
                amount_str = amount_str.replace('(', '-').replace(')', '')
                try:
                    amount = float(amount_str)
                except ValueError:
                    continue
                parsed = parse_description(raw)
                merchant = parsed['merchant'] or ''
                category = categorize_merchant(merchant)
                if not category:
                    unknown_merchants.add(merchant)
                    category = 'Uncategorized'
                results.append({
                    'date': parsed['date'],
                    'merchant': merchant,
                    'amount': amount,
                    'category_guess': category,
                })
    return results, unknown_merchants
