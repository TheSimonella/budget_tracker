import csv
import re
from datetime import datetime

CATEGORY_KEYWORDS = {
    'Groceries': ['WALMART', 'SAFEWAY', 'GROCERY', 'COSTCO'],
    'Gas': ['SHELL', 'CHEVRON', 'EXXON', 'GAS'],
    'Utilities': ['UTILITY', 'ELECTRIC', 'WATER', 'COMCAST', 'VERIZON'],
    'Rent/Mortgage': ['RENT', 'MORTGAGE']
}

def clean_merchant(text: str) -> str:
    if not text:
        return ''
    text = re.sub(r'\s{2,}.*$', '', text)
    text = re.sub(r'\d{4,}', '', text)
    text = re.sub(r'[^\w\s&]', '', text)
    return text.strip().upper()

def categorize_merchant(merchant: str) -> str:
    up = merchant.upper()
    for name, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in up:
                return name
    return 'Uncategorized'

def parse_bank1(rows):
    records = []
    for row in rows:
        date = datetime.strptime(row['Date'], '%Y-%m-%d').date()
        amount = float(row['Amount'])
        tx_type = 'income' if amount > 0 else 'expense'
        merchant = clean_merchant(row.get('Description', ''))
        records.append({
            'amount': abs(amount),
            'transaction_type': tx_type,
            'description': row.get('Description', ''),
            'merchant': merchant,
            'date': date,
            'category_name': categorize_merchant(merchant)
        })
    return records

def parse_bank2(rows):
    records = []
    for row in rows:
        credit = row.get('Credit', '') or '0'
        debit = row.get('Debit', '') or '0'
        amount = float(credit) - float(debit)
        desc = row.get('Details', '')
        date_str = row.get('Transaction Date') or row.get('Date')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        merchant = clean_merchant(desc)
        records.append({
            'amount': abs(amount),
            'transaction_type': 'income' if amount > 0 else 'expense',
            'description': desc,
            'merchant': merchant,
            'date': date,
            'category_name': categorize_merchant(merchant)
        })
    return records

def parse_csv(path: str, bank: str = 'bank1'):
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if bank == 'bank2':
        return parse_bank2(rows)
    return parse_bank1(rows)
